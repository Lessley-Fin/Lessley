using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Models;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IVerificationCodeRepository
{
    /// <summary>The single live code document for this flow and address, or null.</summary>
    Task<VerificationCode?> GetAsync(VerificationPurpose purpose, string normalizedEmail, CancellationToken ct = default);

    Task AddAsync(VerificationCode code, CancellationToken ct = default);

    Task UpdateAsync(VerificationCode code, CancellationToken ct = default);

    Task DeleteAsync(VerificationCode code, CancellationToken ct = default);

    Task DeleteAllForUserAsync(string userId, CancellationToken ct = default);
}
