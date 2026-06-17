using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;

namespace Lessley.Gateway.Api.Consumers;

public class UserCategoriesCalculatedEventConsumer : IConsumer<UserCategoriesCalculatedEvent>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly ILogger<UserCategoriesCalculatedEventConsumer> _logger;

    public UserCategoriesCalculatedEventConsumer(ISendNotificationService sendNotificationService, ILogger<UserCategoriesCalculatedEventConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<UserCategoriesCalculatedEvent> context)
    {
        var msg = context.Message;
        await _sendNotificationService.SendToUserAsync(msg.UserId, "Your category profile has been updated.", ct: context.CancellationToken);
        _logger.LogInformation("UserCategoriesCalculated notification sent to {UserId}", msg.UserId);
    }
}

public class TopAccountsCalculatedEventConsumer : IConsumer<TopAccountsCalculatedEvent>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly ILogger<TopAccountsCalculatedEventConsumer> _logger;

    public TopAccountsCalculatedEventConsumer(ISendNotificationService sendNotificationService, ILogger<TopAccountsCalculatedEventConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<TopAccountsCalculatedEvent> context)
    {
        var msg = context.Message;
        await _sendNotificationService.SendToUserAsync(msg.UserId, "Your top spending accounts have been analyzed.", ct: context.CancellationToken);
        _logger.LogInformation("TopAccountsCalculated notification sent to {UserId}", msg.UserId);
    }
}

public class TopStoresCalculatedEventConsumer : IConsumer<TopStoresCalculatedEvent>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly ILogger<TopStoresCalculatedEventConsumer> _logger;

    public TopStoresCalculatedEventConsumer(ISendNotificationService sendNotificationService, ILogger<TopStoresCalculatedEventConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<TopStoresCalculatedEvent> context)
    {
        var msg = context.Message;
        await _sendNotificationService.SendToUserAsync(msg.UserId, "Your top spending stores have been analyzed.", ct: context.CancellationToken);
        _logger.LogInformation("TopStoresCalculated notification sent to {UserId}", msg.UserId);
    }
}

public class MissedSavingsCalculatedEventConsumer : IConsumer<MissedSavingsCalculatedEvent>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly ILogger<MissedSavingsCalculatedEventConsumer> _logger;

    public MissedSavingsCalculatedEventConsumer(ISendNotificationService sendNotificationService, ILogger<MissedSavingsCalculatedEventConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<MissedSavingsCalculatedEvent> context)
    {
        var msg = context.Message;
        await _sendNotificationService.SendToUserAsync(msg.UserId, "Missed savings opportunities have been identified.", ct: context.CancellationToken);
        _logger.LogInformation("MissedSavingsCalculated notification sent to {UserId}", msg.UserId);
    }
}

public class MatchingClubsCalculatedEventConsumer : IConsumer<MatchingClubsCalculatedEvent>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly ILogger<MatchingClubsCalculatedEventConsumer> _logger;

    public MatchingClubsCalculatedEventConsumer(ISendNotificationService sendNotificationService, ILogger<MatchingClubsCalculatedEventConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<MatchingClubsCalculatedEvent> context)
    {
        var msg = context.Message;
        await _sendNotificationService.SendToUserAsync(msg.UserId, "Your matching loyalty clubs have been updated.", ct: context.CancellationToken);
        _logger.LogInformation("MatchingClubsCalculated notification sent to {UserId}", msg.UserId);
    }
}
