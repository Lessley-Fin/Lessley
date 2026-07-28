using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using System.Net.Mime;
using System.Security.Cryptography;

namespace Lessley.Gateway.Api.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    [Produces(MediaTypeNames.Application.Json)]
    [EnableRateLimiting("auth")]
    public class AuthController : ControllerBase
    {
        private readonly ApplicationDbContext _context;
        private readonly UserManager<ApplicationUser> _userManager;
        private readonly SignInManager<ApplicationUser> _signInManager;
        private readonly IJwtService _jwtService;
        private readonly AuthConfig _authConfig;

        public AuthController(
            ApplicationDbContext context,
            UserManager<ApplicationUser> userManager,
            SignInManager<ApplicationUser> signInManager,
            IJwtService jwtService,
            IOptions<AuthConfig> authConfig)
        {
            _context       = context;
            _userManager   = userManager;
            _signInManager = signInManager;
            _jwtService    = jwtService;
            _authConfig    = authConfig.Value;
        }

        /// <summary>Registers a new user account with the Viewer role.</summary>
        [HttpPost("register")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        public async Task<IActionResult> Register([FromBody] RegisterDto model)
        {
            var user = new ApplicationUser
            {
                UserName      = model.UserName,
                Email         = model.Email,
                Clubs         = model.Clubs ?? new(),
                MutedTags     = model.MutedCategories ?? new(),
                MatchingScore = model.MatchLevel?.ToMatchingScore(),
            };
            var result = await _userManager.CreateAsync(user, model.Password);
            if (!result.Succeeded) return BadRequest(result.Errors);

            result = await _userManager.AddToRoleAsync(user, Enums.UserRoles.Viewer.ToString());
            if (!result.Succeeded) return BadRequest(result.Errors);

            return Ok();
        }

        /// <summary>Authenticates a user and issues httpOnly session cookies.</summary>
        /// <remarks>Tokens are never returned in the body — they are set as Secure/HttpOnly
        /// cookies. The response body carries only non-sensitive profile info for the UI.</remarks>
        [HttpPost("login")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        public async Task<IActionResult> Login([FromBody] LoginDto model)
        {
            var user = await _userManager.FindByNameAsync(model.UserName);
            if (user == null)
                return Unauthorized("Invalid credentials");

            // Counts failures and enforces lockout (configured in AddPersistenceWithIdentity).
            var signIn = await _signInManager.CheckPasswordSignInAsync(user, model.Password, lockoutOnFailure: true);
            if (signIn.IsLockedOut)
                return Unauthorized("Account temporarily locked due to repeated failed logins. Try again later.");
            if (!signIn.Succeeded)
                return Unauthorized("Invalid credentials");

            var accessToken            = await _jwtService.GenerateAccessToken(user);
            var (rawRefresh, refreshEntity) = _jwtService.GenerateRefreshToken(user.Id);

            _context.RefreshTokens.Add(refreshEntity);
            await _context.SaveChangesAsync();

            SetAuthCookies(accessToken, rawRefresh);

            var roles = await GetUserRolesAsync(user.Id);
            return Ok(new { userName = user.UserName, email = user.Email, userId = user.Id, roles });
        }

        /// <summary>Rotates the refresh cookie and issues a fresh access cookie.</summary>
        /// <remarks>Reads the refresh token from the httpOnly cookie. On reuse of an already
        /// rotated token, every refresh token for that user is revoked (theft response).</remarks>
        [HttpPost("refresh")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        public async Task<IActionResult> Refresh()
        {
            var rawRefresh = Request.Cookies[AuthCookieNames.Refresh];
            if (string.IsNullOrEmpty(rawRefresh))
                return Unauthorized("Missing refresh token");

            var hash = _jwtService.HashToken(rawRefresh);
            var tokenEntity = await _context.RefreshTokens.FirstOrDefaultAsync(r => r.Token == hash);

            if (tokenEntity == null)
            {
                ClearAuthCookies();
                return Unauthorized("Invalid refresh token");
            }

            // Presenting an already-revoked token means it was rotated away — treat as theft
            // and revoke the whole chain for that user.
            if (tokenEntity.Revoked != null)
            {
                await RevokeAllForUserAsync(tokenEntity.UserId);
                ClearAuthCookies();
                return Unauthorized("Refresh token reuse detected");
            }

            if (tokenEntity.IsExpired)
            {
                ClearAuthCookies();
                return Unauthorized("Expired refresh token");
            }

            var user = await _userManager.FindByIdAsync(tokenEntity.UserId);
            if (user == null)
            {
                ClearAuthCookies();
                return Unauthorized();
            }

            var newAccessToken = await _jwtService.GenerateAccessToken(user);

            if (!_authConfig.IsRotateRefresh)
            {
                // Refresh cookie unchanged; just mint a new access + CSRF cookie.
                SetAuthCookies(newAccessToken, rawRefreshToken: null);
            }
            else
            {
                tokenEntity.Revoked = DateTime.UtcNow;
                var (newRaw, newEntity) = _jwtService.GenerateRefreshToken(tokenEntity.UserId);
                _context.RefreshTokens.Update(tokenEntity);
                _context.RefreshTokens.Add(newEntity);
                await _context.SaveChangesAsync();
                SetAuthCookies(newAccessToken, newRaw);
            }

            var roles = await GetUserRolesAsync(user.Id);
            return Ok(new { userName = user.UserName, email = user.Email, userId = user.Id, roles });
        }

        /// <summary>Logs out: revokes the current refresh token and clears all auth cookies.</summary>
        [HttpPost("logout")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        public async Task<IActionResult> Logout()
        {
            var rawRefresh = Request.Cookies[AuthCookieNames.Refresh];
            if (!string.IsNullOrEmpty(rawRefresh))
            {
                var hash = _jwtService.HashToken(rawRefresh);
                var tokenEntity = await _context.RefreshTokens.FirstOrDefaultAsync(r => r.Token == hash);
                if (tokenEntity != null && tokenEntity.Revoked == null)
                {
                    tokenEntity.Revoked = DateTime.UtcNow;
                    _context.RefreshTokens.Update(tokenEntity);
                    await _context.SaveChangesAsync();
                }
            }

            ClearAuthCookies();
            return Ok();
        }

        // ── Helpers ──────────────────────────────────────────────────────────────

        // UserManager.GetRolesAsync emits a Join the MongoDB EF provider can't translate,
        // so resolve roles with the two-step (query + Contains) pattern used elsewhere
        // (JwtService.GenerateAccessToken, AdminController.ChangeUserRole).
        private async Task<List<string>> GetUserRolesAsync(string userId)
        {
            var roleIds = await _context.UserRoles
                .Where(ur => ur.UserId == userId)
                .Select(ur => ur.RoleId)
                .ToListAsync();

            return await _context.Roles
                .Where(r => roleIds.Contains(r.Id))
                .Select(r => r.Name!)
                .ToListAsync();
        }

        private async Task RevokeAllForUserAsync(string userId)
        {
            var active = await _context.RefreshTokens
                .Where(r => r.UserId == userId && r.Revoked == null)
                .ToListAsync();
            var now = DateTime.UtcNow;
            foreach (var t in active) t.Revoked = now;
            if (active.Count > 0)
            {
                _context.RefreshTokens.UpdateRange(active);
                await _context.SaveChangesAsync();
            }
        }

        private void SetAuthCookies(string accessToken, string? rawRefreshToken)
        {
            var secure   = Request.IsHttps;
            var sameSite = ParseSameSite(_authConfig.CookieSameSite);
            var domain   = string.IsNullOrWhiteSpace(_authConfig.CookieDomain) ? null : _authConfig.CookieDomain;

            Response.Cookies.Append(AuthCookieNames.Access, accessToken, new CookieOptions
            {
                HttpOnly = true,
                Secure   = secure,
                SameSite = sameSite,
                Domain   = domain,
                Path     = "/",
                Expires  = DateTimeOffset.UtcNow.AddMinutes(_authConfig.AccessTimeoutMinutes),
            });

            if (rawRefreshToken is not null)
            {
                Response.Cookies.Append(AuthCookieNames.Refresh, rawRefreshToken, new CookieOptions
                {
                    HttpOnly = true,
                    Secure   = secure,
                    SameSite = sameSite,
                    Domain   = domain,
                    Path     = AuthCookieNames.RefreshPath,
                    Expires  = DateTimeOffset.UtcNow.AddHours(_authConfig.RefreshTimeoutHours),
                });
            }

            // Double-submit CSRF token: readable by JS so the SPA can echo it in a header.
            // Hex (URL-safe) so the cookie value is transported verbatim — base64 would be
            // URL-encoded in Set-Cookie and then mismatch the decoded Request.Cookies value.
            var csrf = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
            Response.Cookies.Append(AuthCookieNames.Csrf, csrf, new CookieOptions
            {
                HttpOnly = false,
                Secure   = secure,
                SameSite = sameSite,
                Domain   = domain,
                Path     = "/",
                Expires  = DateTimeOffset.UtcNow.AddHours(_authConfig.RefreshTimeoutHours),
            });
        }

        private void ClearAuthCookies()
        {
            var domain = string.IsNullOrWhiteSpace(_authConfig.CookieDomain) ? null : _authConfig.CookieDomain;
            Response.Cookies.Delete(AuthCookieNames.Access,  new CookieOptions { Path = "/", Domain = domain });
            Response.Cookies.Delete(AuthCookieNames.Refresh, new CookieOptions { Path = AuthCookieNames.RefreshPath, Domain = domain });
            Response.Cookies.Delete(AuthCookieNames.Csrf,    new CookieOptions { Path = "/", Domain = domain });
        }

        private static SameSiteMode ParseSameSite(string value) => value?.Trim().ToLowerInvariant() switch
        {
            "none" => SameSiteMode.None,
            "lax"  => SameSiteMode.Lax,
            _      => SameSiteMode.Strict,
        };
    }
}
