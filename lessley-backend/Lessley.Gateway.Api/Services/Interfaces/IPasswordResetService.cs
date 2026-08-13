using Lessley.Gateway.Api.Models.Auth;

namespace Lessley.Gateway.Api.Services.Interfaces;

/// <summary>
/// Emailed password reset, in three steps so the code is proved once and the new password is
/// sent separately. Every step answers the same way for unknown addresses — an attacker cannot
/// use this flow to learn who has an account.
/// </summary>
public interface IPasswordResetService
{
    /// <summary>Emails a reset code if the address has an account. Always reports success.</summary>
    Task<AuthOperationResult> RequestAsync(ForgotPasswordDto dto, CancellationToken ct = default);

    /// <summary>Trades a valid code for a single-use reset ticket.</summary>
    Task<AuthOperationResult> VerifyCodeAsync(VerifyPasswordResetCodeDto dto, CancellationToken ct = default);

    /// <summary>Sets the new password against the ticket and invalidates every existing session.</summary>
    Task<AuthOperationResult> ResetAsync(ResetPasswordDto dto, CancellationToken ct = default);
}
