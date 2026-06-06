using Lessley.Gateway.Api.Models;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface INotificationRepository
{
    Task SaveAsync(Notification notification, CancellationToken ct = default);
    Task<List<Notification>> GetByUserAsync(string userId, CancellationToken ct = default);
    Task MarkAllAsReadAsync(string userId, CancellationToken ct = default);
}
