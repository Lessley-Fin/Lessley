using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;
using Microsoft.AspNetCore.Identity;

namespace Lessley.Gateway.Api.Consumers;

public class DealUserNotificationConsumer : IConsumer<DealUserNotification>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly ILogger<DealUserNotificationConsumer> _logger;

    public DealUserNotificationConsumer(
        ISendNotificationService sendNotificationService,
        UserManager<ApplicationUser> userManager,
        ILogger<DealUserNotificationConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _userManager             = userManager;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<DealUserNotification> context)
    {
        var email = context.Message.UserId;

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
        {
            _logger.LogWarning("DealUserNotification: user {Email} not found — skipping", email);
            return;
        }

        await _sendNotificationService.SendToUserAsync(
            user.Id, context.Message.Message, context.Message.DealId, context.CancellationToken);

        _logger.LogInformation(
            "DealUserNotification consumed — user {UserId} ({Email}), deal '{DealId}'",
            user.Id, email, context.Message.DealId);
    }
}
