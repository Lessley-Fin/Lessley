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
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IPublishEndpoint _bus;
    private readonly IHttpContextAccessor _httpContextAccessor;
    private readonly ILogger<SendNotificationService> _logger;

    public SendNotificationService(
        IHubContext<NotificationHub> hubContext,
        IConnectionManager connectionManager,
        INotificationRepository notificationRepository,
        UserManager<ApplicationUser> userManager,
        IPublishEndpoint bus,
        IHttpContextAccessor httpContextAccessor,
        ILogger<SendNotificationService> logger)
    {
        _hubContext             = hubContext;
        _connectionManager      = connectionManager;
        _notificationRepository = notificationRepository;
        _userManager            = userManager;
        _bus                    = bus;
        _httpContextAccessor    = httpContextAccessor;
        _logger                 = logger;
    }

    public async Task<int> SendToUserAsync(string userId, string message, string? dealId = null, CancellationToken ct = default)
    {
        var sentAt  = DateTime.UtcNow;
        var payload = new { timestamp = sentAt, message, dealId, type = "user" };

        var connections = _connectionManager.GetConnections(userId).ToList();
        foreach (var connectionId in connections)
            await _hubContext.Clients.Client(connectionId).SendAsync("DealUserNotification", payload, ct);

        await _notificationRepository.SaveAsync(new Notification
        {
            UserId  = userId,
            Message = message,
            DealId  = dealId,
            Type    = "user",
            SentAt  = sentAt,
        }, ct);

        _logger.LogInformation("DealUserNotification sent to user {UserId} ({Count} live connections)", userId, connections.Count);
        await PublishDispatchedEventAsync("user:" + userId, "user", connections.Count, sentAt, ct);
        return connections.Count;
    }

    public async Task SendToGroupAsync(string groupTag, string message, string? dealId = null, CancellationToken ct = default)
    {
        var sentAt  = DateTime.UtcNow;
        var payload = new { timestamp = sentAt, message, dealId, type = "group", group = groupTag };

        await _hubContext.Clients.Group(groupTag).SendAsync("DealGroupNotification", payload, ct);

        var userEmails = await _userManager.Users
            .Where(u => u.Tags != null && u.Tags.Contains(groupTag) &&
                        (u.MutedTags == null || !u.MutedTags.Contains(groupTag)))
            .Select(u => u.Email!)
            .ToListAsync(ct);

        if (userEmails.Count > 0)
        {
            var notifications = userEmails.Select(email => new Notification
            {
                UserId     = email,
                Message    = message,
                DealId     = dealId,
                Categories = new List<string> { groupTag },
                Type       = "group",
                SentAt     = sentAt,
            });
            await _notificationRepository.SaveManyAsync(notifications, ct);
        }

        _logger.LogInformation(
            "DealGroupNotification sent to group '{Group}' — {Count} notification(s) created",
            groupTag, userEmails.Count);
        await PublishDispatchedEventAsync("group:" + groupTag, "group", userEmails.Count, sentAt, ct);
    }

    public async Task SendDealNotificationAsync(string dealId, string message, string[] categories, CancellationToken ct = default)
    {
        var sentAt = DateTime.UtcNow;

        var userEmails = await _userManager.Users
            .Where(u => u.Tags != null &&
                        u.Tags.Any(t => categories.Contains(t)) &&
                        (u.MutedTags == null || !categories.All(c => u.MutedTags.Contains(c))))
            .Select(u => u.Email!)
            .Distinct()
            .ToListAsync(ct);

        var payload       = new { timestamp = sentAt, message, dealId, categories, type = "deal" };
        var notifications = new List<Notification>(userEmails.Count);

        foreach (var email in userEmails)
        {
            var connections = _connectionManager.GetConnections(email).ToList();
            foreach (var conn in connections)
                await _hubContext.Clients.Client(conn).SendAsync("DealGroupNotification", payload, ct);

            notifications.Add(new Notification
            {
                UserId     = email,
                Message    = message,
                DealId     = dealId,
                Categories = categories.ToList(),
                Type       = "deal",
                SentAt     = sentAt,
            });
        }

        if (notifications.Count > 0)
            await _notificationRepository.SaveManyAsync(notifications, ct);

        _logger.LogInformation(
            "DealNotification sent for deal '{DealId}' — {Count} recipients across categories: {Categories}",
            dealId, userEmails.Count, string.Join(", ", categories));
        await PublishDispatchedEventAsync("deal:" + dealId, "deal", userEmails.Count, sentAt, ct);
    }

    public async Task<int> SendCalcNotificationAsync(string userId, string calcType, string message, string? data = null, CancellationToken ct = default)
    {
        var sentAt  = DateTime.UtcNow;
        var payload = new { timestamp = sentAt, message, calcType, type = "calc" };

        var connections = _connectionManager.GetConnections(userId).ToList();
        foreach (var connectionId in connections)
            await _hubContext.Clients.Client(connectionId).SendAsync("CalcNotification", payload, ct);

        await _notificationRepository.SaveAsync(new Notification
        {
            UserId   = userId,
            Message  = message,
            Type     = "calc",
            CalcType = calcType,
            Data     = data,
            SentAt   = sentAt,
        }, ct);

        _logger.LogInformation("CalcNotification ({CalcType}) stored for user {UserId} ({Count} live connections)", calcType, userId, connections.Count);
        await PublishDispatchedEventAsync("calc:" + calcType + ":" + userId, "calc", connections.Count, sentAt, ct);
        return connections.Count;
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
            _logger.LogWarning(ex, "Failed to publish NotificationDispatchedEvent for {NotificationId}", notificationId);
        }
    }
}
