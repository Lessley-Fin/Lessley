namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IPersonalizationService
{
    Task RecalculateCategoriesAsync(string userId, CancellationToken ct = default);
    Task TriggerCalculateTopAccountsAsync(string userId, CancellationToken ct = default);
    Task TriggerCalculateTopStoresAsync(string userId, CancellationToken ct = default);
    Task TriggerCalculateMissedSavingsAsync(string userId, CancellationToken ct = default);
    Task TriggerCalculateMatchingClubsAsync(string userId, CancellationToken ct = default);
    Task TriggerCalculateClubCategoriesAsync(string clubId, CancellationToken ct = default);
}
