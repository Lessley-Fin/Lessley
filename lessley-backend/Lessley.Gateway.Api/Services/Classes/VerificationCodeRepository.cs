using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.EntityFrameworkCore;

namespace Lessley.Gateway.Api.Services.Classes;

public class VerificationCodeRepository : IVerificationCodeRepository
{
    private readonly ApplicationDbContext _db;

    public VerificationCodeRepository(ApplicationDbContext db) => _db = db;

    public Task<VerificationCode?> GetAsync(
        VerificationPurpose purpose, string normalizedEmail, CancellationToken ct = default)
    {
        // Compared against the stored string rather than an enum so the MongoDB EF provider
        // sees a plain equality on a string field.
        var purposeName = purpose.ToString();
        return _db.VerificationCodes
            .FirstOrDefaultAsync(c => c.Purpose == purposeName && c.NormalizedEmail == normalizedEmail, ct);
    }

    public async Task AddAsync(VerificationCode code, CancellationToken ct = default)
    {
        _db.VerificationCodes.Add(code);
        await _db.SaveChangesAsync(ct);
    }

    public async Task UpdateAsync(VerificationCode code, CancellationToken ct = default)
    {
        _db.VerificationCodes.Update(code);
        await _db.SaveChangesAsync(ct);
    }

    public async Task DeleteAsync(VerificationCode code, CancellationToken ct = default)
    {
        _db.VerificationCodes.Remove(code);
        await _db.SaveChangesAsync(ct);
    }

    public async Task DeleteByEmailAsync(string normalizedEmail, CancellationToken ct = default)
    {
        var codes = await _db.VerificationCodes
            .Where(c => c.NormalizedEmail == normalizedEmail)
            .ToListAsync(ct);

        if (codes.Count == 0) return;

        _db.VerificationCodes.RemoveRange(codes);
        await _db.SaveChangesAsync(ct);
    }
}
