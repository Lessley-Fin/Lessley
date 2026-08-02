using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;

namespace Lessley.Gateway.Api.Consumers;

public class DealNotificationConsumer : IConsumer<DealNotification>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly ILogger<DealNotificationConsumer> _logger;

    public DealNotificationConsumer(
        ISendNotificationService sendNotificationService,
        ILogger<DealNotificationConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<DealNotification> context)
    {
        var msg = context.Message;

        await _sendNotificationService.SendDealNotificationAsync(
            msg.DealId, msg.Message, msg.Categories, context.CancellationToken);

        _logger.LogInformation(
            "DealNotification consumed — deal '{DealId}', categories: {Categories}",
            msg.DealId, string.Join(", ", msg.Categories));
    }
}
