using Lessley.Gateway.Api.Models;
using MongoDB.Bson;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface INotificationReadRepository
{
    Task SaveAsync(NotificationRead record, CancellationToken ct = default);
    Task SaveManyAsync(IEnumerable<NotificationRead> records, CancellationToken ct = default);
    Task<List<NotificationRead>> GetByUserAsync(string userId, CancellationToken ct = default);
    Task MarkAllAsReadAsync(string userId, CancellationToken ct = default);
    Task<bool> MarkAsReadAsync(ObjectId notificationId, string userId, CancellationToken ct = default);
}
