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
        private readonly bool _isRotateRefresh;

        public AuthController(
            ApplicationDbContext context,
            UserManager<ApplicationUser> userManager,
            IJwtService jwtService,
            IOptions<AuthConfig> authConfig)
        {
            _context         = context;
            _userManager     = userManager;
            _jwtService      = jwtService;
            _isRotateRefresh = authConfig.Value.IsRotateRefresh;
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

        /// <summary>Authenticates a user and returns a JWT access token and a refresh token.</summary>
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
        /// <remarks>When rotation is enabled, a new refresh token is also issued and the old one is revoked.</remarks>
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

    }
}
