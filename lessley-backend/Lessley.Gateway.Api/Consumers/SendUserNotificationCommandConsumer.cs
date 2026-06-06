using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;

namespace Lessley.Gateway.Api.Consumers;

public class SendUserNotificationCommandConsumer : IConsumer<SendUserNotificationCommand>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly ILogger<SendUserNotificationCommandConsumer> _logger;

    public SendUserNotificationCommandConsumer(
        ISendNotificationService sendNotificationService,
        ILogger<SendUserNotificationCommandConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<SendUserNotificationCommand> context)
    {
        var (userId, message) = (context.Message.UserId, context.Message.Message);

        await _sendNotificationService.SendToUserAsync(userId, message, context.CancellationToken);

        _logger.LogInformation(
            "SendUserNotificationCommand consumed — sent to user '{UserId}': {Message}",
            userId, message);
    }
}
