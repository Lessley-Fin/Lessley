using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;

namespace Lessley.Gateway.Api.Services.Classes;

/// <summary>
/// Asynchronous work handed to Personalization. There is deliberately no HTTP path here —
/// client traffic reaches Personalization through Caddy, and server-to-server work goes
/// over RabbitMQ so neither service depends on the other being reachable.
/// </summary>
public class PersonalizationService : IPersonalizationService
{
    private readonly IPublishEndpoint _bus;
    private readonly ILogger<PersonalizationService> _logger;

    public PersonalizationService(
        IPublishEndpoint bus,
        ILogger<PersonalizationService> logger)
    {
        _bus    = bus;
        _logger = logger;
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
