using Lessley.Gateway.Api.Models;
using Microsoft.AspNetCore.Identity;

namespace Lessley.Gateway.Api.Services.Interfaces
{
    public interface IJwtService
    {
        public Task<string> GenerateAccessToken(IdentityUser user);

        // Returns the raw token (sent to the client once, in a cookie) alongside the
        // entity to persist — the entity stores only a hash of the raw token.
        public (string RawToken, RefreshToken Entity) GenerateRefreshToken(string userId);

        // Hashes a raw refresh token the same way it is stored, for lookup/comparison.
        public string HashToken(string rawToken);
    }
}
