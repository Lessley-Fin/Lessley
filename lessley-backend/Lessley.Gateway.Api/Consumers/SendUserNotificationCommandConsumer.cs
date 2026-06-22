using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;

namespace Lessley.Gateway.Api.Consumers;

public class DealUserNotificationConsumer : IConsumer<DealUserNotification>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly ILogger<DealUserNotificationConsumer> _logger;

    public DealUserNotificationConsumer(
        ISendNotificationService sendNotificationService,
        ILogger<DealUserNotificationConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<DealUserNotification> context)
    {
        var msg = context.Message;

        await _sendNotificationService.SendToUserAsync(msg.UserId, msg.Message, msg.DealId, context.CancellationToken);

        _logger.LogInformation(
            "DealUserNotification consumed — user '{UserId}', deal '{DealId}'",
            msg.UserId, msg.DealId);
    }
}
