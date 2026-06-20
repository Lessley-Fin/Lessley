using Lessley.Gateway.Api.Models;
using MongoDB.Bson;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface INotificationService
{
    Task<List<NotificationDto>> GetUserNotificationsAsync(string userId, CancellationToken ct = default);
    Task MarkAllAsReadAsync(string userId, CancellationToken ct = default);
    Task<bool> MarkAsReadAsync(ObjectId notificationId, string userId, CancellationToken ct = default);
    Task<Notification?> GetLatestCalcAsync(string userId, string calcType, CancellationToken ct = default);
}
