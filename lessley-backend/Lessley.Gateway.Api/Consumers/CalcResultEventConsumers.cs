using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;
using Microsoft.AspNetCore.Identity;
using System.Text.Json;

namespace Lessley.Gateway.Api.Consumers;

public class MissedSavingsCalculatedEventConsumer : IConsumer<MissedSavingsCalculatedEvent>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly ILogger<MissedSavingsCalculatedEventConsumer> _logger;

    public MissedSavingsCalculatedEventConsumer(
        ISendNotificationService sendNotificationService,
        UserManager<ApplicationUser> userManager,
        ILogger<MissedSavingsCalculatedEventConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _userManager             = userManager;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<MissedSavingsCalculatedEvent> context)
    {
        var email = context.Message.UserId;

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
        {
            _logger.LogWarning("MissedSavingsCalculated: user {Email} not found — skipping", email);
            return;
        }

        var data = context.Message.Data.HasValue
            ? JsonSerializer.Serialize(context.Message.Data.Value)
            : null;

        await _sendNotificationService.SendCalcNotificationAsync(
            email, "missed-savings", "Missed savings opportunities have been identified.", data, context.CancellationToken);

        _logger.LogInformation("MissedSavingsCalculated stored for {Email}", email);
    }
}

public class MatchingClubsCalculatedEventConsumer : IConsumer<MatchingClubsCalculatedEvent>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly ILogger<MatchingClubsCalculatedEventConsumer> _logger;

    public MatchingClubsCalculatedEventConsumer(
        ISendNotificationService sendNotificationService,
        UserManager<ApplicationUser> userManager,
        ILogger<MatchingClubsCalculatedEventConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _userManager             = userManager;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<MatchingClubsCalculatedEvent> context)
    {
        var email = context.Message.UserId;

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
        {
            _logger.LogWarning("MatchingClubsCalculated: user {Email} not found — skipping", email);
            return;
        }

        var data = context.Message.Data.HasValue
            ? JsonSerializer.Serialize(context.Message.Data.Value)
            : null;

        await _sendNotificationService.SendCalcNotificationAsync(
            email, "matching-clubs", "Your matching loyalty clubs have been updated.", data, context.CancellationToken);

        _logger.LogInformation("MatchingClubsCalculated stored for {Email}", email);
    }
}
