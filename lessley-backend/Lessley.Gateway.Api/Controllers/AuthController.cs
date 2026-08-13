using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Middleware;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using System.Net.Mime;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;

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
        private readonly IAuthSessionService _sessions;
        private readonly AuthConfig _authConfig;

        public AuthController(
            ApplicationDbContext context,
            UserManager<ApplicationUser> userManager,
            SignInManager<ApplicationUser> signInManager,
            IJwtService jwtService,
            IAuthSessionService sessions,
            IOptions<AuthConfig> authConfig)
        {
            _context       = context;
            _userManager   = userManager;
            _signInManager = signInManager;
            _jwtService    = jwtService;
            _sessions      = sessions;
            _authConfig    = authConfig.Value;
        }

        // Registration lives in RegistrationController, which stages it across start /
        // verify-email / complete. There is deliberately no single-shot register endpoint here:
        // creating the account in one call is what allowed abandoned signups to leave real,
        // unverified users behind.

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

            var session = await _sessions.IssueAsync(user);
            SetAuthCookies(session.AccessToken, session.RawRefreshToken);

            return Ok(new
            {
                userName = session.Profile.UserName,
                email    = session.Profile.Email,
                userId   = session.Profile.UserId,
                roles    = session.Profile.Roles,
            });
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
                await _sessions.RevokeAllRefreshTokensAsync(tokenEntity.UserId);
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

            var roles = await _sessions.GetRolesAsync(user.Id);
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

        /// <summary>Edge authentication check — called by Caddy's forward_auth, never by a client.</summary>
        /// <remarks>
        /// Caddy issues this as a GET sub-request carrying the original request's cookies and
        /// headers, then copies <c>X-Auth-Email</c> from the response onto the upstream request.
        /// This is the single place identity is established for services that sit behind the
        /// edge — they trust that header and never a client-supplied value.
        /// </remarks>
        [HttpGet("verify")]
        [Authorize]
        // Runs once per proxied request, so the class-level "auth" policy (5/min) would break
        // the app almost immediately. The edge already rate-limits the originating request.
        [DisableRateLimiting]
        [ProducesResponseType(StatusCodes.Status204NoContent)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        [ProducesResponseType(StatusCodes.Status403Forbidden)]
        public IActionResult Verify()
        {
            // The sub-request is always a GET, so CsrfProtectionMiddleware skips it. Apply the
            // same double-submit check here against the *original* method, which Caddy forwards.
            var originalMethod = Request.Headers["X-Forwarded-Method"].ToString();
            var originalPath   = new PathString(Request.Headers["X-Forwarded-Uri"].ToString().Split('?')[0]);
            if (!string.IsNullOrEmpty(originalMethod) &&
                !CsrfProtectionMiddleware.IsSafeMethod(originalMethod) &&
                !CsrfProtectionMiddleware.IsAnonymousAuthPath(originalPath) &&
                !string.IsNullOrEmpty(Request.Cookies[AuthCookieNames.Access]))
            {
                var headerToken = Request.Headers[AuthCookieNames.CsrfHeader].ToString();
                var cookieToken = Request.Cookies[AuthCookieNames.Csrf];

                if (string.IsNullOrEmpty(headerToken) ||
                    string.IsNullOrEmpty(cookieToken) ||
                    !CryptographicOperations.FixedTimeEquals(
                        Encoding.UTF8.GetBytes(headerToken),
                        Encoding.UTF8.GetBytes(cookieToken)))
                {
                    return StatusCode(StatusCodes.Status403Forbidden, new { detail = "CSRF validation failed" });
                }
            }

            var email = User.FindFirstValue(ClaimTypes.Email);
            if (string.IsNullOrEmpty(email)) return Unauthorized();

            Response.Headers["X-Auth-Email"] = email;
            return NoContent();
        }

        // ── Helpers ──────────────────────────────────────────────────────────────
        // Cookie shaping lives in AuthCookieWriter, shared with the registration and
        // OTP-login controllers so every sign-in path emits identical cookies.

        private void SetAuthCookies(string accessToken, string? rawRefreshToken)
            => AuthCookieWriter.SetAuthCookies(Request, Response, _authConfig, accessToken, rawRefreshToken);

        private void ClearAuthCookies()
            => AuthCookieWriter.ClearAuthCookies(Response, _authConfig);
    }
}
