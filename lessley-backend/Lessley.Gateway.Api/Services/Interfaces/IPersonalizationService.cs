namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IPersonalizationService
{
    /// <summary>Recalculates user categories via HTTP call to the Personalization service.</summary>
    Task RecalculateCategoriesAsync(string userId, CancellationToken ct = default);

    /// <summary>Publishes a missed-savings recommendation command via RabbitMQ.</summary>
    Task TriggerCalculateMissedSavingsAsync(string userId, CancellationToken ct = default);

    /// <summary>Publishes a matching-clubs recommendation command via RabbitMQ.</summary>
    Task TriggerCalculateMatchingClubsAsync(string userId, CancellationToken ct = default);
}
