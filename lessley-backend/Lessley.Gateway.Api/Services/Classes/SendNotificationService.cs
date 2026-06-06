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

    public async Task<int> SendToUserAsync(string userId, string message, CancellationToken ct = default)
    {
        var connections = _connectionManager.GetConnections(userId).ToList();
        if (connections.Count == 0)
            return 0;

        var sentAt  = DateTime.UtcNow;
        var payload = new { timestamp = sentAt, message, type = "notification" };

        foreach (var connectionId in connections)
            await _hubContext.Clients.Client(connectionId).SendAsync("ReceiveNotification", payload, ct);

        await _notificationRepository.SaveAsync(new Notification
        {
            TargetId   = userId,
            TargetType = "user",
            Message    = message,
            SentAt     = sentAt,
        }, ct);

        _logger.LogInformation("Notification sent to user {UserId} ({Count} connections): {Message}",
            userId, connections.Count, message);

        return connections.Count;
    }

    public async Task SendToGroupAsync(string groupTag, string message, CancellationToken ct = default)
    {
        var sentAt  = DateTime.UtcNow;
        var payload = new { timestamp = sentAt, message, type = "group_notification", group = groupTag };

        await _hubContext.Clients.Group(groupTag).SendAsync("ReceiveNotification", payload, ct);

        await _notificationRepository.SaveAsync(new Notification
        {
            TargetId   = groupTag,
            TargetType = "group",
            Message    = message,
            SentAt     = sentAt,
        }, ct);

        _logger.LogInformation("Notification sent to group '{Group}': {Message}", groupTag, message);
    }
}
