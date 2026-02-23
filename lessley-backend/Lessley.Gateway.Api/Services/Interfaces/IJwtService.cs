using Lessley.Gateway.Api.Models;
using Microsoft.AspNetCore.Identity;

namespace Lessley.Gateway.Api.Services.Interfaces
{
    public interface IJwtService
    {
        public Task<string> GenerateAccessToken(IdentityUser user);

        public RefreshToken GenerateRefreshToken(string userId);
    }
}
