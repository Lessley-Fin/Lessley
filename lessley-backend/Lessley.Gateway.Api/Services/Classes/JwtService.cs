using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;

namespace Lessley.Gateway.Api.Services.Classes
{
    public class JwtService : IJwtService
    {
        private readonly ApplicationDbContext _context;
        private readonly JwtConfig _jwtConfig;
        private readonly AuthConfig _authConfig;

        public JwtService(ApplicationDbContext context, IOptions<AuthConfig> authConfig, IOptions<JwtConfig> jwtConfig)
        {
            _context = context;
            _jwtConfig = jwtConfig.Value;
            _authConfig = authConfig.Value;
        }

        public async Task<string> GenerateAccessToken(IdentityUser user)
        {
            var userRoleIds = await _context.UserRoles
                            .Where(ur => ur.UserId == user.Id)
                            .Select(ur => ur.RoleId)
                            .ToListAsync();

            var roles = await _context.Roles
                .Where(r => userRoleIds.Contains(r.Id))
                .Select(r => r.Name)
                .ToListAsync();

            var claims = new List<Claim>()
            {
                new Claim(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()),
                new Claim(ClaimTypes.NameIdentifier, user.Id),
                new Claim(ClaimTypes.Name, user.UserName ?? string.Empty),
                new Claim(ClaimTypes.Email, user.Email ?? string.Empty),
            };

            foreach (var role in roles)
            {
                if (Enum.TryParse<UserRoles>(role, out var parsedRole))
                {
                    claims.Add(new Claim(ClaimTypes.Role, parsedRole.ToString()));
                }
            }

            var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(_jwtConfig.Key));
            var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

            var token = new JwtSecurityToken(
                issuer: _jwtConfig.Issuer,
                audience: _jwtConfig.Audience,
                claims: claims,
                expires: DateTime.UtcNow.AddMinutes(_authConfig.AccessTimeoutMinutes),
                signingCredentials: creds
            );

            return new JwtSecurityTokenHandler().WriteToken(token);
        }

        public (string RawToken, RefreshToken Entity) GenerateRefreshToken(string userId)
        {
            var randomBytes = RandomNumberGenerator.GetBytes(64);
            var rawToken = Convert.ToBase64String(randomBytes);
            DateTime now = DateTime.UtcNow;

            // Persist only the hash: a database leak then yields no usable refresh tokens.
            var entity = new RefreshToken
            {
                Token = HashToken(rawToken),
                UserId = userId,
                Expires = now.AddHours(_authConfig.RefreshTimeoutHours),
                Created = now
            };

            return (rawToken, entity);
        }

        public string HashToken(string rawToken)
        {
            var hash = SHA256.HashData(Encoding.UTF8.GetBytes(rawToken));
            return Convert.ToBase64String(hash);
        }
    }
}
