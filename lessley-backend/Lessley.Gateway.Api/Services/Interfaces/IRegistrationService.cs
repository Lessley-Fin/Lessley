using Lessley.Gateway.Api.Models.Auth;

namespace Lessley.Gateway.Api.Services.Interfaces;

/// <summary>
/// The four-call registration handshake. No <c>ApplicationUser</c> exists until
/// <see cref="CompleteAsync"/> succeeds — everything before it lives in a self-expiring
/// pending document, so an abandoned signup leaves nothing behind and has to start over.
/// </summary>
public interface IRegistrationService
{
    /// <summary>Validates the credentials, stores them pending, and emails a verification code.</summary>
    Task<AuthOperationResult> StartAsync(StartRegistrationDto dto, CancellationToken ct = default);

    /// <summary>Checks the emailed code and marks the pending registration as email-verified.</summary>
    Task<AuthOperationResult> VerifyEmailAsync(VerifyRegistrationDto dto, CancellationToken ct = default);

    /// <summary>Issues a fresh code, subject to the cooldown and per-registration send cap.</summary>
    Task<AuthOperationResult> ResendCodeAsync(ResendRegistrationCodeDto dto, CancellationToken ct = default);

    /// <summary>Creates the real user and returns a session. Requires a verified pending registration.</summary>
    Task<AuthOperationResult> CompleteAsync(CompleteRegistrationDto dto, CancellationToken ct = default);
}
