using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using System.Security.Claims;

namespace Lessley.Gateway.Api.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class AuthController : ControllerBase
    {
        private readonly ApplicationDbContext _context;
        private readonly UserManager<IdentityUser> _userManager;
        private readonly IJwtService _jwtService;
        private readonly IConfiguration _configuration;
        private readonly bool isRotateRefresh;

        public AuthController(
            ApplicationDbContext context,
            UserManager<IdentityUser> userManager,
            IJwtService jwtTokenService,
            IConfiguration config,
            IOptions<AuthConfig> configuration)
        {
            _context = context;
            _userManager = userManager;
            _jwtService = jwtTokenService;
            isRotateRefresh = configuration.Value.IsRotateRefresh;
            _configuration = config;
        }

        [HttpPost("bootstrap")]
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
            var email = _configuration["Bootstrap:Email"] ?? "";

            if (username == "" || password == "" || email == "")
                return BadRequest("Bootstrap failed");

            var register = new RegisterDto() { UserName = username, Email = email, Password = password };
            return await CreateUser(register, UserRoles.Admin);
        }

        [HttpPost("register")]
        public async Task<IActionResult> Register([FromBody] RegisterDto model)
        {
            return await CreateUser(model, UserRoles.Viewer);
        }

        private async Task<IActionResult> CreateUser(RegisterDto model, UserRoles roles)
        {
            var user = new IdentityUser { UserName = model.UserName, Email = model.Email };
            var result = await _userManager.CreateAsync(user, model.Password);

            if (!result.Succeeded)
                return BadRequest(result.Errors);

            result = await _userManager.AddToRoleAsync(user, roles.ToString());
            if (!result.Succeeded)
                return BadRequest(result.Errors);

            return Ok();
        }

        [HttpPost("login")]
        public async Task<IActionResult> Login([FromBody] LoginDto model)
        {
            var user = await _userManager.FindByNameAsync(model.UserName);
            if (user == null || !await _userManager.CheckPasswordAsync(user, model.Password))
                return Unauthorized("Invalid credentials");

            var accessToken = await _jwtService.GenerateAccessToken(user);
            var refreshToken = _jwtService.GenerateRefreshToken(user.Id);

            _context.RefreshTokens.Add(refreshToken);
            await _context.SaveChangesAsync();

            return Ok(new { accessToken, refreshToken = refreshToken.Token });
        }

        [HttpPost("refresh")]
        public async Task<IActionResult> Refresh([FromBody] RefreshRequestDto request)
        {
            var tokenEntity = await _context.RefreshTokens.FirstOrDefaultAsync(r => r.Token == request.RefreshToken);
            if (tokenEntity == null || !tokenEntity.IsActive)
                return Unauthorized("Invalid or expired refresh token");

            var user = await _userManager.FindByIdAsync(tokenEntity.UserId);
            if (user == null) return Unauthorized();

            var newAccessToken = await _jwtService.GenerateAccessToken(user);
            if (!isRotateRefresh)
            {
                return Ok(new { accessToken = newAccessToken, refreshToken = tokenEntity.Token });
            }

            tokenEntity.Revoked = DateTime.UtcNow;
            var newRefreshToken = _jwtService.GenerateRefreshToken(tokenEntity.UserId);
            _context.RefreshTokens.Update(tokenEntity);
            _context.RefreshTokens.Add(newRefreshToken);
            await _context.SaveChangesAsync();

            return Ok(new { accessToken = newAccessToken, refreshToken = newRefreshToken.Token });
        }

        [Authorize]
        [HttpGet("me")]
        public IActionResult GetMyProfile()
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            var userName = User.FindFirstValue(ClaimTypes.Name);
            var email = User.FindFirstValue(ClaimTypes.Email);
            var roles = User.FindAll(ClaimTypes.Role).Select(r => r.Value).ToList();

            return Ok(new { userId, userName, roles });
        }

        [Authorize(Roles = nameof(UserRoles.Admin))]
        [HttpPut("role/{userId}/{newRole}")]
        public async Task<IActionResult> ChangeUserRole([FromRoute] string userId, [FromRoute] UserRoles newRole)
        {
            var user = await _userManager.FindByIdAsync(userId);
            if (user == null) return NotFound("User not found");

            var userRoleIds = await _context.UserRoles
                .Where(ur => ur.UserId == user.Id)
                .Select(ur => ur.RoleId)
                .ToListAsync();

            var currentRoles = await _context.Roles
                .Where(r => userRoleIds.Contains(r.Id))
                .Select(r => r.Name)
                .ToListAsync();

            await _userManager.RemoveFromRolesAsync(user, currentRoles); // remove all old roles
            await _userManager.AddToRoleAsync(user, newRole.ToString()); // add new role

            return Ok($"User role changed to {newRole}");
        }

        [Authorize(Roles = nameof(UserRoles.Admin))]
        [HttpGet("admin-data")]
        public IActionResult GetAdminData()
        {
            return Ok("admin-data");
        }

        [Authorize(Roles = nameof(UserRoles.Admin) + "," + nameof(UserRoles.Operator))]
        [HttpGet("operator-admin-action")]
        public IActionResult OperatorAdminAction()
        {
            return Ok("This endpoint is for Operators and Admins only.");
        }
    }
}
