using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Models;

namespace Lessley.Gateway.Api.Services.Interfaces;

/// <summary>
/// Result of asking for a code. <c>Code</c> is the plaintext to email and is set only when
/// <c>Issued</c> is true; otherwise <c>ThrottleMessage</c> says how long to wait.
/// </summary>
public sealed record CodeIssueOutcome(bool Issued, string? Code, string? ThrottleMessage);

/// <summary>
/// Result of presenting a code. On success <c>Entry</c> is the still-live document, so the caller
/// can hang a reset ticket off it or delete it.
/// </summary>
public sealed record CodeRedemption(bool Success, VerificationCode? Entry, string? FailureMessage);

/// <summary>
/// Owns the emailed one-time codes end to end: generation, keyed hashing, constant-time checking,
/// and the throttling/attempt rules that make a six-digit secret safe to email.
/// </summary>
public interface IVerificationCodeService
{
    /// <summary>A fresh numeric code of the configured length, drawn from a CSPRNG.</summary>
    string GenerateCode();

    /// <summary>A high-entropy opaque token, used for registration handles and reset tickets.</summary>
    string GenerateTicket();

    /// <summary>Keyed hash of a code or ticket — only this ever reaches the database.</summary>
    string Hash(string value);

    /// <summary>Constant-time comparison of a presented value against a stored hash.</summary>
    bool Verify(string value, string? storedHash);

    /// <summary>
    /// Creates or replaces the live code for a flow and address, enforcing the resend cooldown
    /// and send cap. Replacing rather than adding is what stops an older code still working.
    /// </summary>
    Task<CodeIssueOutcome> IssueAsync(
        VerificationPurpose purpose, string normalizedEmail, string userId, CancellationToken ct = default);

    /// <summary>
    /// Checks a presented code, counting the failure against the attempt budget and burning the
    /// code once that budget is spent.
    /// </summary>
    Task<CodeRedemption> RedeemAsync(
        VerificationPurpose purpose, string normalizedEmail, string code, CancellationToken ct = default);
}
