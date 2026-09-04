using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.EntityFrameworkCore;

namespace Lessley.Gateway.Api.Services.Classes;

public class AuthSessionService : IAuthSessionService
{
    private readonly ApplicationDbContext _db;
    private readonly IJwtService _jwtService;

    public AuthSessionService(ApplicationDbContext db, IJwtService jwtService)
    {
        _db         = db;
        _jwtService = jwtService;
    }

    public async Task<AuthSession> IssueAsync(ApplicationUser user, CancellationToken ct = default)
    {
        var accessToken = await _jwtService.GenerateAccessToken(user);
        var (rawRefresh, refreshEntity) = _jwtService.GenerateRefreshToken(user.Id);

        _db.RefreshTokens.Add(refreshEntity);
        await _db.SaveChangesAsync(ct);

        var roles = await GetRolesAsync(user.Id, ct);
        return new AuthSession(accessToken, rawRefresh,
            new AuthProfile(user.UserName, user.Email, user.Id, roles));
    }

    public async Task RevokeAllRefreshTokensAsync(string userId, CancellationToken ct = default)
    {
        var active = await _db.RefreshTokens
            .Where(r => r.UserId == userId && r.Revoked == null)
            .ToListAsync(ct);

        if (active.Count == 0) return;

        var now = DateTime.UtcNow;
        foreach (var token in active) token.Revoked = now;

        _db.RefreshTokens.UpdateRange(active);
        await _db.SaveChangesAsync(ct);
    }

    public async Task DeleteAllRefreshTokensAsync(string userId, CancellationToken ct = default)
    {
        var owned = await _db.RefreshTokens
            .Where(r => r.UserId == userId)
            .ToListAsync(ct);

        if (owned.Count == 0) return;

        _db.RefreshTokens.RemoveRange(owned);
        await _db.SaveChangesAsync(ct);
    }

    // UserManager.GetRolesAsync emits a Join the MongoDB EF provider cannot translate, so roles
    // are resolved with the two-step (query + Contains) pattern used elsewhere in the Gateway.
    public async Task<List<string>> GetRolesAsync(string userId, CancellationToken ct = default)
    {
        var roleIds = await _db.UserRoles
            .Where(ur => ur.UserId == userId)
            .Select(ur => ur.RoleId)
            .ToListAsync(ct);

        return await _db.Roles
            .Where(r => roleIds.Contains(r.Id) && r.Name != null)
            .Select(r => r.Name!)
            .ToListAsync(ct);
    }
}
