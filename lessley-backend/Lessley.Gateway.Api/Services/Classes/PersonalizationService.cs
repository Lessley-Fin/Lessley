using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;

namespace Lessley.Gateway.Api.Services.Classes;

public class PersonalizationService : IPersonalizationService
{
    private readonly IPublishEndpoint _bus;
    private readonly ILogger<PersonalizationService> _logger;

    public PersonalizationService(IPublishEndpoint bus, ILogger<PersonalizationService> logger)
    {
        _bus    = bus;
        _logger = logger;
    }

    public async Task RecalculateCategoriesAsync(string userId, CancellationToken ct = default)
    {
        _logger.LogInformation("Publishing CalculateUserCategoriesCommand for {UserId}", userId);
        await _bus.Publish(new CalculateUserCategoriesCommand(userId), ct);
    }

    public async Task TriggerCalculateTopAccountsAsync(string userId, CancellationToken ct = default)
    {
        _logger.LogInformation("Publishing CalculateTopAccountsCommand for {UserId}", userId);
        await _bus.Publish(new CalculateTopAccountsCommand(userId), ct);
    }

    public async Task TriggerCalculateTopStoresAsync(string userId, CancellationToken ct = default)
    {
        _logger.LogInformation("Publishing CalculateTopStoresCommand for {UserId}", userId);
        await _bus.Publish(new CalculateTopStoresCommand(userId), ct);
    }

    public async Task TriggerCalculateMissedSavingsAsync(string userId, CancellationToken ct = default)
    {
        _logger.LogInformation("Publishing CalculateMissedSavingsCommand for {UserId}", userId);
        await _bus.Publish(new CalculateMissedSavingsCommand(userId), ct);
    }

    public async Task TriggerCalculateMatchingClubsAsync(string userId, CancellationToken ct = default)
    {
        _logger.LogInformation("Publishing CalculateMatchingClubsCommand for {UserId}", userId);
        await _bus.Publish(new CalculateMatchingClubsCommand(userId), ct);
    }

    public async Task TriggerCalculateClubCategoriesAsync(string clubId, CancellationToken ct = default)
    {
        _logger.LogInformation("Publishing CalculateClubCategoriesCommand for {ClubId}", clubId);
        await _bus.Publish(new CalculateClubCategoriesCommand(clubId), ct);
    }
}
