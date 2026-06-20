using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;

namespace Lessley.Gateway.Api.Services.Classes;

public class PersonalizationService : IPersonalizationService
{
    private readonly IPublishEndpoint _bus;
    private readonly IPersonalizationProxyService _proxy;
    private readonly ILogger<PersonalizationService> _logger;

    public PersonalizationService(
        IPublishEndpoint bus,
        IPersonalizationProxyService proxy,
        ILogger<PersonalizationService> logger)
    {
        _bus    = bus;
        _proxy  = proxy;
        _logger = logger;
    }

    // Categories are HTTP-only — fire-and-forget call to the Personalization service.
    public async Task RecalculateCategoriesAsync(string userId, CancellationToken ct = default)
    {
        _logger.LogInformation("Triggering category recalculation via HTTP for {UserId}", userId);
        var response = await _proxy.GetInsightsCategoriesAsync(userId, ct: ct);
        if (!response.IsSuccessStatusCode)
            _logger.LogWarning("Category recalculation returned {StatusCode} for {UserId}", response.StatusCode, userId);
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
}
