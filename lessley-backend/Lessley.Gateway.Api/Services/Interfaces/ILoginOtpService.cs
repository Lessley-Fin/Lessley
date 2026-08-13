using Lessley.Gateway.Api.Models.Auth;

namespace Lessley.Gateway.Api.Services.Interfaces;

/// <summary>
/// Passwordless sign-in: prove control of the mailbox and get the same session a password login
/// would produce. Offered alongside password login, not instead of it.
/// </summary>
public interface ILoginOtpService
{
    /// <summary>Emails a sign-in code if the address has an account. Always reports success.</summary>
    Task<AuthOperationResult> RequestAsync(RequestLoginCodeDto dto, CancellationToken ct = default);

    /// <summary>Redeems the code for a session.</summary>
    Task<AuthOperationResult> VerifyAsync(VerifyLoginCodeDto dto, CancellationToken ct = default);
}
