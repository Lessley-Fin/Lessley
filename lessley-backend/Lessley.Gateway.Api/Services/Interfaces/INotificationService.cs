using Lessley.Gateway.Api.Models;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface INotificationService
{
    Task<List<Notification>> GetUserNotificationsAsync(string userId, CancellationToken ct = default);
    Task MarkUserNotificationsAsReadAsync(string userId, CancellationToken ct = default);
}
