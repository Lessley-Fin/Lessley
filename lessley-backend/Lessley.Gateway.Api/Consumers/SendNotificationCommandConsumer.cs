using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;

namespace Lessley.Gateway.Api.Consumers;

public class SendNotificationCommandConsumer : IConsumer<SendGroupNotificationCommand>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly ILogger<SendNotificationCommandConsumer> _logger;

    public SendNotificationCommandConsumer(
        ISendNotificationService sendNotificationService,
        ILogger<SendNotificationCommandConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<SendGroupNotificationCommand> context)
    {
        var (groupTag, message) = (context.Message.GroupTag, context.Message.Message);

        await _sendNotificationService.SendToGroupAsync(groupTag, message, context.CancellationToken);

        _logger.LogInformation(
            "SendGroupNotificationCommand consumed — broadcast to group '{Group}': {Message}",
            groupTag, message);
    }
}
