namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IPersonalizationService
{
    /// <summary>
    /// Triggers recalculation of the user's preferred categories in Personalization.
    /// Personalization computes, trims by match level, and posts the new tags back to the Gateway
    /// (PUT /api/user/{email}/tags), which updates the DB and re-syncs SignalR groups.
    /// </summary>
    Task RecalculateCategoriesAsync(string email, CancellationToken ct = default);
}
