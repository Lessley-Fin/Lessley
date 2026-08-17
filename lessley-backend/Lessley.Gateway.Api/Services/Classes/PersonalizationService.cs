using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;

namespace Lessley.Gateway.Api.Services.Classes;

/// <summary>
/// Asynchronous work handed to Personalization. There is deliberately no HTTP path here —
/// client traffic reaches Personalization through Caddy, and server-to-server work goes
/// over RabbitMQ so neither service depends on the other being reachable.
/// </summary>
/// <remarks>
/// One command remains. Missed-savings and club matching used to be published here too, and
/// their answers came back as stored notifications the client polled for; both are now
/// ordinary GETs the client makes through the edge.
/// </remarks>
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

    /// <remarks>
    /// Best-effort on purpose. Every caller is completing something the user is waiting on — a
    /// signup, a bank journey, a settings save — and none of them should fail because the bus
    /// is unreachable. A dropped recalculation is recoverable: the stored categories stay valid
    /// meanwhile, and the next trigger recomputes them.
    /// </remarks>
    public async Task TriggerCalculateUserCategoriesAsync(string userId, int days = 90, CancellationToken ct = default)
    {
        try
        {
            _logger.LogInformation("Publishing CalculateUserCategoriesCommand for {UserId}", userId);
            await _bus.Publish(new CalculateUserCategoriesCommand(userId, days), ct);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to publish CalculateUserCategoriesCommand for {UserId}", userId);
        }
    }
}
