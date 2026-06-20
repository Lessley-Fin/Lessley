using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using MongoDB.Bson;

namespace Lessley.Gateway.Api.Services.Classes;

public class NotificationService : INotificationService
{
    private readonly INotificationRepository _notificationRepository;

    public NotificationService(INotificationRepository notificationRepository)
    {
        _notificationRepository = notificationRepository;
    }

    public async Task<List<NotificationDto>> GetUserNotificationsAsync(string userId, CancellationToken ct = default)
    {
        var notifications = await _notificationRepository.GetByUserAsync(userId, ct);
        return notifications.Select(NotificationDto.From).ToList();
    }

    public Task MarkAllAsReadAsync(string userId, CancellationToken ct = default)
        => _notificationRepository.MarkAllAsReadAsync(userId, ct);

    public Task<bool> MarkAsReadAsync(ObjectId notificationId, string userId, CancellationToken ct = default)
        => _notificationRepository.MarkAsReadAsync(notificationId, userId, ct);

    public Task<Notification?> GetLatestCalcAsync(string userId, string calcType, CancellationToken ct = default)
        => _notificationRepository.GetLatestCalcAsync(userId, calcType, ct);
}
