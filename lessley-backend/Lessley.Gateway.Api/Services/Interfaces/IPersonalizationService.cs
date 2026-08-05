namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IPersonalizationService
{
    /// <summary>Publishes a missed-savings recommendation command via RabbitMQ.</summary>
    Task TriggerCalculateMissedSavingsAsync(string userId, bool timeFilter = true, int days = 7, CancellationToken ct = default);

    /// <summary>Publishes a matching-clubs recommendation command via RabbitMQ.</summary>
    Task TriggerCalculateMatchingClubsAsync(string userId, CancellationToken ct = default);
}
