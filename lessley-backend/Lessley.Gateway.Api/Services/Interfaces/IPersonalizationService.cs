namespace Lessley.Gateway.Api.Services.Interfaces;

/// <summary>
/// HTTP client to the Personalization service. The Gateway is the only component the client
/// talks to, so it proxies Personalization-backed work (recalculation and read-only insights).
/// </summary>
public interface IPersonalizationService
{
    /// <summary>
    /// Process 2 — trigger recalculation of the user's preferred categories based on their
    /// match level. Personalization computes, trims, and posts the new tags back to the Gateway
    /// (PUT /api/user/{email}/tags), which updates the DB and SignalR groups.
    /// </summary>
    Task RecalculateCategoriesAsync(string email, CancellationToken ct = default);

    /// <summary>
    /// Process 7 — request club recommendations asynchronously. Returns immediately; the
    /// computation runs in the background and Personalization notifies the Gateway on completion
    /// (which creates a user notification).
    /// </summary>
    Task RequestClubRecommendationsAsync(string email, CancellationToken ct = default);

    /// <summary>Process 4 — preferred accounts (read-only).</summary>
    Task<string> GetPreferredAccountsAsync(string email, CancellationToken ct = default);

    /// <summary>Process 5 — preferred stores (read-only).</summary>
    Task<string> GetPreferredStoresAsync(string email, CancellationToken ct = default);

    /// <summary>Process 6 — alternative stores / missed savings (read-only).</summary>
    Task<string> GetAlternativeStoresAsync(string email, CancellationToken ct = default);

    /// <summary>Process 10 — transaction breakdown by MCC (read-only).</summary>
    Task<string> GetTransactionBreakdownByMccAsync(string email, CancellationToken ct = default);
}
