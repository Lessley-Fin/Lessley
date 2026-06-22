using Lessley.Gateway.Api.Models;
using MongoDB.Bson;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface INotificationRepository
{
    Task SaveAsync(Notification notification, CancellationToken ct = default);
    Task<List<Notification>> GetByIdsAsync(IEnumerable<ObjectId> ids, CancellationToken ct = default);
}
