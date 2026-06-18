using Lessley.Gateway.Api.Hubs;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.SignalR;
using Microsoft.EntityFrameworkCore;

namespace Lessley.Gateway.Api.Services.Classes;

public class SendNotificationService : ISendNotificationService
{
    private readonly IHubContext<NotificationHub> _hubContext;
    private readonly IConnectionManager _connectionManager;
    private readonly INotificationRepository _notificationRepository;
    private readonly INotificationReadRepository _readRepository;
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly ILogger<SendNotificationService> _logger;

    public SendNotificationService(
        IHubContext<NotificationHub> hubContext,
        IConnectionManager connectionManager,
        INotificationRepository notificationRepository,
        INotificationReadRepository readRepository,
        UserManager<ApplicationUser> userManager,
        ILogger<SendNotificationService> logger)
    {
        _hubContext             = hubContext;
        _connectionManager      = connectionManager;
        _notificationRepository = notificationRepository;
        _readRepository         = readRepository;
        _userManager            = userManager;
        _logger                 = logger;
    }

    public async Task<int> SendToUserAsync(string userId, string message, string? dealId = null, CancellationToken ct = default)
    {
        var connections = _connectionManager.GetConnections(userId).ToList();
        var sentAt      = DateTime.UtcNow;
        var payload     = new { timestamp = sentAt, message, dealId, type = "user" };

        foreach (var connectionId in connections)
            await _hubContext.Clients.Client(connectionId).SendAsync("DealUserNotification", payload, ct);

        var notification = new Notification
        {
            TargetId   = userId,
            TargetType = "user",
            Message    = message,
            DealId     = dealId,
            SentAt     = sentAt,
        };
        await _notificationRepository.SaveAsync(notification, ct);

        await _readRepository.SaveAsync(new NotificationRead
        {
            NotificationId = notification.Id,
            UserId         = userId,
            IsRead         = false,
            CreatedAt      = sentAt,
        }, ct);

        _logger.LogInformation("DealUserNotification sent to user {UserId} ({Count} live connections)", userId, connections.Count);

        return connections.Count;
    }

    public async Task SendToGroupAsync(string groupTag, string message, string? dealId = null, CancellationToken ct = default)
    {
        var sentAt  = DateTime.UtcNow;
        var payload = new { timestamp = sentAt, message, dealId, type = "group", group = groupTag };

        await _hubContext.Clients.Group(groupTag).SendAsync("DealGroupNotification", payload, ct);

        var notification = new Notification
        {
            TargetId   = groupTag,
            TargetType = "group",
            Message    = message,
            DealId     = dealId,
            SentAt     = sentAt,
        };
        await _notificationRepository.SaveAsync(notification, ct);

        // Fanout: create a NotificationRead record for every user who currently has this tag
        // and hasn't muted it. This captures the "interest-at-send" snapshot so that tag
        // changes later don't erase notification history.
        var userIds = await _userManager.Users
            .Where(u => u.Tags != null && u.Tags.Contains(groupTag) &&
                        (u.MutedTags == null || !u.MutedTags.Contains(groupTag)))
            .Select(u => u.Id)
            .ToListAsync(ct);

        if (userIds.Count > 0)
        {
            var reads = userIds.Select(uid => new NotificationRead
            {
                NotificationId = notification.Id,
                UserId         = uid,
                IsRead         = false,
                CreatedAt      = sentAt,
            });
            await _readRepository.SaveManyAsync(reads, ct);
        }

        _logger.LogInformation(
            "DealGroupNotification sent to group '{Group}' — {Count} notification_read record(s) created",
            groupTag, userIds.Count);
    }
}
