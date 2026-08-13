using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.EntityFrameworkCore;

namespace Lessley.Gateway.Api.Services.Classes;

public class PendingRegistrationRepository : IPendingRegistrationRepository
{
    private readonly ApplicationDbContext _db;

    public PendingRegistrationRepository(ApplicationDbContext db) => _db = db;

    public Task<PendingRegistration?> GetByTokenHashAsync(string tokenHash, CancellationToken ct = default)
        => _db.PendingRegistrations.FirstOrDefaultAsync(p => p.TokenHash == tokenHash, ct);

    public Task<PendingRegistration?> GetByNormalizedEmailAsync(string normalizedEmail, CancellationToken ct = default)
        => _db.PendingRegistrations.FirstOrDefaultAsync(p => p.NormalizedEmail == normalizedEmail, ct);

    public Task<bool> UserNameTakenAsync(string normalizedUserName, CancellationToken ct = default)
        => _db.PendingRegistrations.AnyAsync(p => p.NormalizedUserName == normalizedUserName, ct);

    public async Task AddAsync(PendingRegistration registration, CancellationToken ct = default)
    {
        _db.PendingRegistrations.Add(registration);
        await _db.SaveChangesAsync(ct);
    }

    public async Task UpdateAsync(PendingRegistration registration, CancellationToken ct = default)
    {
        _db.PendingRegistrations.Update(registration);
        await _db.SaveChangesAsync(ct);
    }

    public async Task DeleteAsync(PendingRegistration registration, CancellationToken ct = default)
    {
        _db.PendingRegistrations.Remove(registration);
        await _db.SaveChangesAsync(ct);
    }

    public async Task DeleteByEmailOrUserNameAsync(
        string normalizedEmail, string normalizedUserName, CancellationToken ct = default)
    {
        var stale = await _db.PendingRegistrations
            .Where(p => p.NormalizedEmail == normalizedEmail || p.NormalizedUserName == normalizedUserName)
            .ToListAsync(ct);

        if (stale.Count == 0) return;

        _db.PendingRegistrations.RemoveRange(stale);
        await _db.SaveChangesAsync(ct);
    }
}
