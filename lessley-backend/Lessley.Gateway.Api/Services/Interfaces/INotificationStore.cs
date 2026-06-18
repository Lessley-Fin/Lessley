using Lessley.Gateway.Api.Models;
using MongoDB.Bson;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface INotificationRepository
{
    Task SaveAsync(Notification notification, CancellationToken ct = default);
    Task SaveManyAsync(IEnumerable<Notification> notifications, CancellationToken ct = default);
    Task<List<Notification>> GetByUserAsync(string userId, CancellationToken ct = default);
    Task<bool> MarkAsReadAsync(ObjectId id, string userId, CancellationToken ct = default);
    Task MarkAllAsReadAsync(string userId, CancellationToken ct = default);
}
