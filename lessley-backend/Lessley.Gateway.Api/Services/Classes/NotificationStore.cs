using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.EntityFrameworkCore;

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

    public async Task<List<Notification>> GetByUserAsync(string userId, CancellationToken ct = default)
        => await _db.Notifications
            .Where(n => n.TargetId == userId && n.TargetType == "user")
            .OrderByDescending(n => n.SentAt)
            .ToListAsync(ct);

    public async Task MarkAllAsReadAsync(string userId, CancellationToken ct = default)
    {
        var notifications = await _db.Notifications
            .Where(n => n.TargetId == userId && n.TargetType == "user" && !n.IsRead)
            .ToListAsync(ct);

        foreach (var n in notifications)
            n.IsRead = true;

        await _db.SaveChangesAsync(ct);
    }
}
