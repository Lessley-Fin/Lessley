using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Hubs;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;
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
    private readonly IPublishEndpoint _bus;
    private readonly IHttpContextAccessor _httpContextAccessor;
    private readonly ILogger<SendNotificationService> _logger;

    public SendNotificationService(
        IHubContext<NotificationHub> hubContext,
        IConnectionManager connectionManager,
        INotificationRepository notificationRepository,
        INotificationReadRepository readRepository,
        UserManager<ApplicationUser> userManager,
        IPublishEndpoint bus,
        IHttpContextAccessor httpContextAccessor,
        ILogger<SendNotificationService> logger)
    {
        _hubContext             = hubContext;
        _connectionManager      = connectionManager;
        _notificationRepository = notificationRepository;
        _readRepository         = readRepository;
        _userManager            = userManager;
        _bus                    = bus;
        _httpContextAccessor    = httpContextAccessor;
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

        await PublishDispatchedEventAsync(notification.Id.ToString(), "user", connections.Count, sentAt, ct);

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

        await PublishDispatchedEventAsync(notification.Id.ToString(), "group", userIds.Count, sentAt, ct);
    }

    public async Task SendDealNotificationAsync(string dealId, string message, string[] categories, CancellationToken ct = default)
    {
        var sentAt  = DateTime.UtcNow;

        // Find all users subscribed to ANY of the deal's categories without muting them all.
        var userIds = await _userManager.Users
            .Where(u => u.Tags != null &&
                        u.Tags.Any(t => categories.Contains(t)) &&
                        (u.MutedTags == null || !categories.All(c => u.MutedTags.Contains(c))))
            .Select(u => u.Id)
            .Distinct()
            .ToListAsync(ct);

        var notification = new Notification
        {
            TargetId   = dealId,
            TargetType = "deal",
            Message    = message,
            DealId     = dealId,
            Categories = categories.ToList(),
            SentAt     = sentAt,
        };
        await _notificationRepository.SaveAsync(notification, ct);

        var payload = new { timestamp = sentAt, message, dealId, categories, type = "deal" };

        foreach (var userId in userIds)
        {
            var connections = _connectionManager.GetConnections(userId).ToList();
            foreach (var conn in connections)
                await _hubContext.Clients.Client(conn).SendAsync("DealGroupNotification", payload, ct);

            await _readRepository.SaveAsync(new NotificationRead
            {
                NotificationId = notification.Id,
                UserId         = userId,
                IsRead         = false,
                CreatedAt      = sentAt,
            }, ct);
        }

        _logger.LogInformation(
            "DealNotification sent for deal '{DealId}' — {Count} recipients across categories: {Categories}",
            dealId, userIds.Count, string.Join(", ", categories));

        await PublishDispatchedEventAsync(notification.Id.ToString(), "deal", userIds.Count, sentAt, ct);
    }

    private async Task PublishDispatchedEventAsync(string notificationId, string type, int recipientCount, DateTime sentAt, CancellationToken ct)
    {
        var requestId = _httpContextAccessor.HttpContext?.TraceIdentifier ?? Guid.NewGuid().ToString();
        try
        {
            await _bus.Publish(new NotificationDispatchedEvent(notificationId, type, recipientCount, requestId, sentAt), ct);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to publish NotificationDispatchedEvent for notification {Id}", notificationId);
        }
    }
}
