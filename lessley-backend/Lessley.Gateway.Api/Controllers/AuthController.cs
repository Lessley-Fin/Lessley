using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using System.Net.Mime;
using System.Security.Claims;

namespace Lessley.Gateway.Api.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    [Produces(MediaTypeNames.Application.Json)]
    public class AuthController : ControllerBase
    {
        private readonly ApplicationDbContext _context;
        private readonly UserManager<ApplicationUser> _userManager;
        private readonly IJwtService _jwtService;
        private readonly IConfiguration _configuration;
        private readonly bool _isRotateRefresh;

        public AuthController(
            ApplicationDbContext context,
            UserManager<ApplicationUser> userManager,
            IJwtService jwtService,
            IConfiguration config,
            IOptions<AuthConfig> authConfig)
        {
            _context         = context;
            _userManager     = userManager;
            _jwtService      = jwtService;
            _configuration   = config;
            _isRotateRefresh = authConfig.Value.IsRotateRefresh;
        }

        /// <summary>One-time admin bootstrap. Creates the initial admin user from app configuration.</summary>
        /// <remarks>Fails if any users already exist, preventing repeated bootstrapping.</remarks>
        /// <param name="key">Optional secret key configured in <c>Bootstrap:Key</c> — required when set.</param>
        [HttpPost("bootstrap")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        public async Task<IActionResult> Bootstrap([FromQuery] string? key = null)
        {
            var bootstrapKey = _configuration["Bootstrap:Key"];
            if (bootstrapKey != null && key != bootstrapKey)
                return Unauthorized("Invalid bootstrap key");

            var count = await _userManager.Users.CountAsync();
            if (count > 0)
                return BadRequest("Bootstrap already completed.");

            var username = _configuration["Bootstrap:Username"] ?? "";
            var password = _configuration["Bootstrap:Password"] ?? "";
            var email    = _configuration["Bootstrap:Email"]    ?? "";

            if (username == "" || password == "" || email == "")
                return BadRequest("Bootstrap configuration is incomplete.");

            return await CreateUser(new RegisterDto { UserName = username, Email = email, Password = password }, UserRoles.Admin);
        }

        /// <summary>Registers a new user account with the Viewer role.</summary>
        /// <param name="model">Registration details: username, email, password, and optional clubs/categories.</param>
        [HttpPost("register")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        public async Task<IActionResult> Register([FromBody] RegisterDto model)
            => await CreateUser(model, UserRoles.Viewer);

        /// <summary>Authenticates a user and returns a JWT access token and a refresh token.</summary>
        /// <param name="model">Login credentials (username and password).</param>
        [HttpPost("login")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        public async Task<IActionResult> Login([FromBody] LoginDto model)
        {
            var user = await _userManager.FindByNameAsync(model.UserName);
            if (user == null || !await _userManager.CheckPasswordAsync(user, model.Password))
                return Unauthorized("Invalid credentials");

            var accessToken  = await _jwtService.GenerateAccessToken(user);
            var refreshToken = _jwtService.GenerateRefreshToken(user.Id);

            _context.RefreshTokens.Add(refreshToken);
            await _context.SaveChangesAsync();

            return Ok(new { accessToken, refreshToken = refreshToken.Token });
        }

        /// <summary>Exchanges a valid refresh token for a new JWT access token.</summary>
        /// <remarks>When refresh token rotation is enabled, a new refresh token is also issued and the old one is revoked.</remarks>
        /// <param name="request">The current refresh token.</param>
        [HttpPost("refresh")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        public async Task<IActionResult> Refresh([FromBody] RefreshRequestDto request)
        {
            var tokenEntity = await _context.RefreshTokens.FirstOrDefaultAsync(r => r.Token == request.RefreshToken);
            if (tokenEntity == null || !tokenEntity.IsActive)
                return Unauthorized("Invalid or expired refresh token");

            var user = await _userManager.FindByIdAsync(tokenEntity.UserId);
            if (user == null) return Unauthorized();

            var newAccessToken = await _jwtService.GenerateAccessToken(user);
            if (!_isRotateRefresh)
                return Ok(new { accessToken = newAccessToken, refreshToken = tokenEntity.Token });

            tokenEntity.Revoked = DateTime.UtcNow;
            var newRefreshToken = _jwtService.GenerateRefreshToken(tokenEntity.UserId);
            _context.RefreshTokens.Update(tokenEntity);
            _context.RefreshTokens.Add(newRefreshToken);
            await _context.SaveChangesAsync();

            return Ok(new { accessToken = newAccessToken, refreshToken = newRefreshToken.Token });
        }

        /// <summary>Returns the authenticated user's profile (ID, username, email, roles).</summary>
        [Authorize]
        [HttpGet("me")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        public IActionResult GetMyProfile()
        {
            var userId   = User.FindFirstValue(ClaimTypes.NameIdentifier);
            var userName = User.FindFirstValue(ClaimTypes.Name);
            var email    = User.FindFirstValue(ClaimTypes.Email);
            var roles    = User.FindAll(ClaimTypes.Role).Select(r => r.Value).ToList();

            return Ok(new { userId, userName, email, roles });
        }

        /// <summary>Changes a user's role. Admin only.</summary>
        /// <param name="email">The email of the user whose role should change.</param>
        /// <param name="newRole">The target role to assign (<c>Admin</c> or <c>Viewer</c>).</param>
        [Authorize(Roles = nameof(UserRoles.Admin))]
        [HttpPut("role/{email}/{newRole}")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        [ProducesResponseType(StatusCodes.Status403Forbidden)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<IActionResult> ChangeUserRole([FromRoute] string email, [FromRoute] UserRoles newRole)
        {
            var user = await _userManager.FindByEmailAsync(email);
            if (user == null) return NotFound("User not found");

            var userRoleIds = await _context.UserRoles
                .Where(ur => ur.UserId == user.Id)
                .Select(ur => ur.RoleId)
                .ToListAsync();

            var currentRoles = await _context.Roles
                .Where(r => userRoleIds.Contains(r.Id))
                .Select(r => r.Name!)
                .ToListAsync();

            await _userManager.RemoveFromRolesAsync(user, currentRoles);
            await _userManager.AddToRoleAsync(user, newRole.ToString());

            return Ok($"User role changed to {newRole}");
        }

        private async Task<IActionResult> CreateUser(RegisterDto model, UserRoles role)
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

            result = await _userManager.AddToRoleAsync(user, role.ToString());
            if (!result.Succeeded) return BadRequest(result.Errors);

            return Ok();
        }
    }
}
