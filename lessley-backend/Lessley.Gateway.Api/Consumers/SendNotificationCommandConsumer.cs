using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;

namespace Lessley.Gateway.Api.Consumers;

public class DealTagNotificationConsumer : IConsumer<DealGroupNotification>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly ILogger<DealTagNotificationConsumer> _logger;

    public DealTagNotificationConsumer(
        ISendNotificationService sendNotificationService,
        ILogger<DealTagNotificationConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<DealGroupNotification> context)
    {
        var msg = context.Message;

        await _sendNotificationService.SendToGroupAsync(msg.GroupTag, msg.Message, msg.DealId, context.CancellationToken);

        _logger.LogInformation(
            "DealGroupNotification consumed — group '{Group}', deal '{DealId}'",
            msg.GroupTag, msg.DealId);
    }
}
