using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;
using Microsoft.AspNetCore.Identity;

namespace Lessley.Gateway.Api.Consumers;

public class UserCategoriesCalculatedEventConsumer : IConsumer<UserCategoriesCalculatedEvent>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly ILogger<UserCategoriesCalculatedEventConsumer> _logger;

    public UserCategoriesCalculatedEventConsumer(
        ISendNotificationService sendNotificationService,
        UserManager<ApplicationUser> userManager,
        ILogger<UserCategoriesCalculatedEventConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _userManager             = userManager;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<UserCategoriesCalculatedEvent> context)
    {
        var email = context.Message.UserId;

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
        {
            _logger.LogWarning("UserCategoriesCalculated: user {Email} not found — skipping", email);
            return;
        }

        await _sendNotificationService.SendToUserAsync(
            user.Id, "Your category profile has been updated.", ct: context.CancellationToken);

        _logger.LogInformation("UserCategoriesCalculated notification sent to {UserId} ({Email})", user.Id, email);
    }
}

public class TopAccountsCalculatedEventConsumer : IConsumer<TopAccountsCalculatedEvent>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly ILogger<TopAccountsCalculatedEventConsumer> _logger;

    public TopAccountsCalculatedEventConsumer(
        ISendNotificationService sendNotificationService,
        UserManager<ApplicationUser> userManager,
        ILogger<TopAccountsCalculatedEventConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _userManager             = userManager;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<TopAccountsCalculatedEvent> context)
    {
        var email = context.Message.UserId;

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
        {
            _logger.LogWarning("TopAccountsCalculated: user {Email} not found — skipping", email);
            return;
        }

        await _sendNotificationService.SendToUserAsync(
            user.Id, "Your top spending accounts have been analyzed.", ct: context.CancellationToken);

        _logger.LogInformation("TopAccountsCalculated notification sent to {UserId} ({Email})", user.Id, email);
    }
}

public class TopStoresCalculatedEventConsumer : IConsumer<TopStoresCalculatedEvent>
{
    private readonly ISendNotificationService _sendNotificationService;
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly ILogger<TopStoresCalculatedEventConsumer> _logger;

    public TopStoresCalculatedEventConsumer(
        ISendNotificationService sendNotificationService,
        UserManager<ApplicationUser> userManager,
        ILogger<TopStoresCalculatedEventConsumer> logger)
    {
        _sendNotificationService = sendNotificationService;
        _userManager             = userManager;
        _logger                  = logger;
    }

    public async Task Consume(ConsumeContext<TopStoresCalculatedEvent> context)
    {
        var email = context.Message.UserId;

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
        {
            _logger.LogWarning("TopStoresCalculated: user {Email} not found — skipping", email);
            return;
        }

        await _sendNotificationService.SendToUserAsync(
            user.Id, "Your top spending stores have been analyzed.", ct: context.CancellationToken);

        _logger.LogInformation("TopStoresCalculated notification sent to {UserId} ({Email})", user.Id, email);
    }
}

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

        await _sendNotificationService.SendToUserAsync(
            user.Id, "Missed savings opportunities have been identified.", ct: context.CancellationToken);

        _logger.LogInformation("MissedSavingsCalculated notification sent to {UserId} ({Email})", user.Id, email);
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

        await _sendNotificationService.SendToUserAsync(
            user.Id, "Your matching loyalty clubs have been updated.", ct: context.CancellationToken);

        _logger.LogInformation("MatchingClubsCalculated notification sent to {UserId} ({Email})", user.Id, email);
    }
}
