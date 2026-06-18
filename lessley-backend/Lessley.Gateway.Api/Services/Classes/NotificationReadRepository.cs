using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.EntityFrameworkCore;
using MongoDB.Bson;

namespace Lessley.Gateway.Api.Services.Classes;

public class NotificationReadRepository : INotificationReadRepository
{
    private readonly ApplicationDbContext _db;

    public NotificationReadRepository(ApplicationDbContext db) => _db = db;

    public async Task SaveAsync(NotificationRead record, CancellationToken ct = default)
    {
        _db.NotificationReads.Add(record);
        await _db.SaveChangesAsync(ct);
    }

    public async Task SaveManyAsync(IEnumerable<NotificationRead> records, CancellationToken ct = default)
    {
        _db.NotificationReads.AddRange(records);
        await _db.SaveChangesAsync(ct);
    }

    public Task<List<NotificationRead>> GetByUserAsync(string userId, CancellationToken ct = default)
        => _db.NotificationReads
              .Where(r => r.UserId == userId)
              .OrderByDescending(r => r.CreatedAt)
              .ToListAsync(ct);

    public async Task MarkAllAsReadAsync(string userId, CancellationToken ct = default)
    {
        var records = await _db.NotificationReads
            .Where(r => r.UserId == userId && !r.IsRead)
            .ToListAsync(ct);

        if (records.Count == 0) return;

        var now = DateTime.UtcNow;
        foreach (var r in records)
        {
            r.IsRead = true;
            r.ReadAt = now;
        }

        await _db.SaveChangesAsync(ct);
    }

    public async Task<bool> MarkAsReadAsync(ObjectId notificationId, string userId, CancellationToken ct = default)
    {
        var record = await _db.NotificationReads
            .FirstOrDefaultAsync(r => r.NotificationId == notificationId && r.UserId == userId, ct);

        if (record is null || record.IsRead)
            return record is not null;

        record.IsRead = true;
        record.ReadAt = DateTime.UtcNow;
        await _db.SaveChangesAsync(ct);
        return true;
    }
}
