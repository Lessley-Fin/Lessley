using Lessley.Gateway.Api.Hubs;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.SignalR;

namespace Lessley.Gateway.Api.Services.Classes;

public class SendNotificationService : ISendNotificationService
{
    private readonly IHubContext<NotificationHub> _hubContext;
    private readonly IConnectionManager _connectionManager;
    private readonly INotificationRepository _notificationRepository;
    private readonly ILogger<SendNotificationService> _logger;

    public SendNotificationService(
        IHubContext<NotificationHub> hubContext,
        IConnectionManager connectionManager,
        INotificationRepository notificationRepository,
        ILogger<SendNotificationService> logger)
    {
        _hubContext             = hubContext;
        _connectionManager      = connectionManager;
        _notificationRepository = notificationRepository;
        _logger                 = logger;
    }

    public async Task<int> SendToUserAsync(string userId, string message, string? dealId = null, CancellationToken ct = default)
    {
        var connections = _connectionManager.GetConnections(userId).ToList();
        var sentAt      = DateTime.UtcNow;
        var payload     = new { timestamp = sentAt, message, dealId, type = "user" };

        foreach (var connectionId in connections)
            await _hubContext.Clients.Client(connectionId).SendAsync("DealUserNotification", payload, ct);

        // Always persist so offline users can read the notification later (Processes 8/9).
        await _notificationRepository.SaveAsync(new Notification
        {
            TargetId   = userId,
            TargetType = "user",
            Message    = message,
            DealId     = dealId,
            SentAt     = sentAt,
        }, ct);

        _logger.LogInformation("DealUserNotification sent to user {UserId} ({Count} live connections)", userId, connections.Count);

        return connections.Count;
    }

    public async Task SendToGroupAsync(string groupTag, string message, string? dealId = null, CancellationToken ct = default)
    {
        var sentAt  = DateTime.UtcNow;
        var payload = new { timestamp = sentAt, message, dealId, type = "group", group = groupTag };

        await _hubContext.Clients.Group(groupTag).SendAsync("DealGroupNotification", payload, ct);

        await _notificationRepository.SaveAsync(new Notification
        {
            TargetId   = groupTag,
            TargetType = "group",
            Message    = message,
            DealId     = dealId,
            SentAt     = sentAt,
        }, ct);

        _logger.LogInformation("DealGroupNotification sent to group '{Group}'", groupTag);
    }
}
