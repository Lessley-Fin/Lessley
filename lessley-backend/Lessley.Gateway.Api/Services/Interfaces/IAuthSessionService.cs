using Lessley.Gateway.Api.Models;

namespace Lessley.Gateway.Api.Services.Interfaces;

/// <summary>The tokens a caller has just earned, plus the non-sensitive profile echoed to the UI.</summary>
public sealed record AuthSession(string AccessToken, string RawRefreshToken, AuthProfile Profile);

public sealed record AuthProfile(string? UserName, string? Email, string UserId, List<string> Roles);

/// <summary>
/// Mints a signed-in session. Shared by every path that can produce one — password login,
/// passwordless OTP login, and the final step of registration — so they all issue identical
/// tokens and the same rotation semantics.
/// </summary>
public interface IAuthSessionService
{
    Task<AuthSession> IssueAsync(ApplicationUser user, CancellationToken ct = default);

    /// <summary>Revokes every live refresh token for a user (password change, theft response).</summary>
    Task RevokeAllRefreshTokensAsync(string userId, CancellationToken ct = default);

    /// <summary>
    /// Removes every refresh token for a user, revoked ones included. Revoking is enough while
    /// the account survives; deletion has to leave nothing keyed to it behind.
    /// </summary>
    Task DeleteAllRefreshTokensAsync(string userId, CancellationToken ct = default);

    Task<List<string>> GetRolesAsync(string userId, CancellationToken ct = default);
}
