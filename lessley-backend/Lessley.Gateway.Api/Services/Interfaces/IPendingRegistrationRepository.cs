using Lessley.Gateway.Api.Models;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IPendingRegistrationRepository
{
    Task<PendingRegistration?> GetByTokenHashAsync(string tokenHash, CancellationToken ct = default);

    Task<PendingRegistration?> GetByNormalizedEmailAsync(string normalizedEmail, CancellationToken ct = default);

    Task<bool> UserNameTakenAsync(string normalizedUserName, CancellationToken ct = default);

    Task AddAsync(PendingRegistration registration, CancellationToken ct = default);

    Task UpdateAsync(PendingRegistration registration, CancellationToken ct = default);

    Task DeleteAsync(PendingRegistration registration, CancellationToken ct = default);

    /// <summary>Drops any pending registrations holding this email or username, whatever their state.</summary>
    Task DeleteByEmailOrUserNameAsync(string normalizedEmail, string normalizedUserName, CancellationToken ct = default);
}
