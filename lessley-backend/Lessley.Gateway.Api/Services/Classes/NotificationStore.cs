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

    public Task<List<Notification>> GetByIdsAsync(IEnumerable<ObjectId> ids, CancellationToken ct = default)
    {
        var idList = ids.ToList();
        return _db.Notifications
            .Where(n => idList.Contains(n.Id))
            .ToListAsync(ct);
    }
}
