using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Hubs;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;
using Microsoft.AspNetCore.SignalR;

namespace Lessley.Gateway.Api.Consumers;

public class SendNotificationCommandConsumer : IConsumer<SendNotificationCommand>
{
    private readonly IHubContext<NotificationHub> _hubContext;
    private readonly INotificationStore _notificationStore;
    private readonly ILogger<SendNotificationCommandConsumer> _logger;

    public SendNotificationCommandConsumer(
        IHubContext<NotificationHub> hubContext,
        INotificationStore notificationStore,
        ILogger<SendNotificationCommandConsumer> logger)
    {
        _hubContext        = hubContext;
        _notificationStore = notificationStore;
        _logger            = logger;
    }

    public async Task Consume(ConsumeContext<SendNotificationCommand> context)
    {
        var (groupTag, message) = (context.Message.GroupTag, context.Message.Message);

        var sentAt  = DateTime.UtcNow;
        var payload = new { timestamp = sentAt, message, type = "group_notification", group = groupTag };

        await _hubContext.Clients.Group(groupTag).SendAsync("ReceiveNotification", payload);

        await _notificationStore.SaveAsync(new Notification
        {
            TargetId       = groupTag,
            TargetType     = "group",
            Message        = message,
            SentAt         = sentAt,
            RecipientCount = 0,
        });

        _logger.LogInformation(
            "SendNotificationCommand consumed — broadcast to group '{Group}': {Message}",
            groupTag, message);
    }
}
