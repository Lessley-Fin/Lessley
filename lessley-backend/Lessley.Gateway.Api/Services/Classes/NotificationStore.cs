using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.EntityFrameworkCore;
using MongoDB.Bson;

namespace Lessley.Gateway.Api.Services.Classes;

public class NotificationRepository : INotificationRepository
{
    private readonly ApplicationDbContext _db;

    public NotificationRepository(ApplicationDbContext db) => _db = db;

    public async Task SaveAsync(Notification notification, CancellationToken ct = default)
    {
        _db.Notifications.Add(notification);
        await _db.SaveChangesAsync(ct);
    }

    public async Task SaveManyAsync(IEnumerable<Notification> notifications, CancellationToken ct = default)
    {
        _db.Notifications.AddRange(notifications);
        await _db.SaveChangesAsync(ct);
    }

    public Task<List<Notification>> GetByUserAsync(string userId, CancellationToken ct = default)
        => _db.Notifications
              .Where(n => n.UserId == userId)
              .OrderByDescending(n => n.SentAt)
              .ToListAsync(ct);

    public async Task<bool> MarkAsReadAsync(ObjectId id, string userId, CancellationToken ct = default)
    {
        var notification = await _db.Notifications
            .FirstOrDefaultAsync(n => n.Id == id && n.UserId == userId, ct);

        if (notification is null || notification.IsRead)
            return notification is not null;

        notification.IsRead = true;
        notification.ReadAt = DateTime.UtcNow;
        await _db.SaveChangesAsync(ct);
        return true;
    }

    public async Task MarkAllAsReadAsync(string userId, CancellationToken ct = default)
    {
        var unread = await _db.Notifications
            .Where(n => n.UserId == userId && !n.IsRead)
            .ToListAsync(ct);

        if (unread.Count == 0) return;

        var now = DateTime.UtcNow;
        foreach (var n in unread)
        {
            n.IsRead = true;
            n.ReadAt = now;
        }

        await _db.SaveChangesAsync(ct);
    }

    public Task<Notification?> GetLatestCalcAsync(string userId, string calcType, CancellationToken ct = default)
        => _db.Notifications
              .Where(n => n.UserId == userId && n.Type == "calc" && n.CalcType == calcType)
              .OrderByDescending(n => n.SentAt)
              .FirstOrDefaultAsync(ct);

    public Task<List<Notification>> GetAllCalcAsync(string userId, CancellationToken ct = default)
        => _db.Notifications
              .Where(n => n.UserId == userId && n.Type == "calc")
              .OrderByDescending(n => n.SentAt)
              .ToListAsync(ct);
}
