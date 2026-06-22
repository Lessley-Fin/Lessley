using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using MongoDB.Bson;

namespace Lessley.Gateway.Api.Services.Classes;

public class NotificationService : INotificationService
{
    private readonly INotificationRepository _notificationRepository;
    private readonly INotificationReadRepository _readRepository;

    public NotificationService(
        INotificationRepository notificationRepository,
        INotificationReadRepository readRepository)
    {
        _notificationRepository = notificationRepository;
        _readRepository         = readRepository;
    }

    public async Task<List<NotificationDto>> GetUserNotificationsAsync(string userId, CancellationToken ct = default)
    {
        var reads = await _readRepository.GetByUserAsync(userId, ct);
        if (reads.Count == 0)
            return [];

        var notificationIds = reads.Select(r => r.NotificationId);
        var notifications   = await _notificationRepository.GetByIdsAsync(notificationIds, ct);

        var notifById = notifications.ToDictionary(n => n.Id);

        return reads
            .Where(r => notifById.ContainsKey(r.NotificationId))
            .Select(r => NotificationDto.From(notifById[r.NotificationId], r))
            .ToList();
    }

    public Task MarkAllAsReadAsync(string userId, CancellationToken ct = default)
        => _readRepository.MarkAllAsReadAsync(userId, ct);

    public Task<bool> MarkAsReadAsync(ObjectId notificationId, string userId, CancellationToken ct = default)
        => _readRepository.MarkAsReadAsync(notificationId, userId, ct);
}
