using Lessley.Gateway.Api.Models.DealSearch;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IDealFinderRepository
{
    Task<(List<DealSearchResult> Results, int Total)> SearchAsync(DealSearchQuery query, CancellationToken ct = default);
    Task<DealSearchResult?> GetByIdAsync(string dealId, CancellationToken ct = default);

    /// <summary>
    /// Hydrates deal ids into deals with their stores, preserving the order of
    /// <paramref name="dealIds"/>. Ids with no deal — or whose store is missing — are dropped.
    /// </summary>
    Task<List<DealSearchResult>> GetByIdsAsync(IReadOnlyList<string> dealIds, CancellationToken ct = default);

    /// <summary>Newest-scraped deals, excluding ids already chosen. The day-one hot fallback.</summary>
    Task<List<DealSearchResult>> RecentlyScrapedAsync(int limit, IReadOnlyCollection<string> excluding, CancellationToken ct = default);

    /// <summary>A random sample of deals scraped since <paramref name="scrapedAfter"/>, excluding ids already chosen.</summary>
    Task<List<DealSearchResult>> RandomDealsAsync(int limit, DateTime scrapedAfter, IReadOnlyCollection<string> excluding, CancellationToken ct = default);

    /// <summary>Every deal id in the catalog. Used by the rollup to prune stats for de-listed deals.</summary>
    Task<List<string>> AllDealIdsAsync(CancellationToken ct = default);

    /// <summary>Every store id in the catalog. Counterpart of <see cref="AllDealIdsAsync"/>.</summary>
    Task<List<string>> AllStoreIdsAsync(CancellationToken ct = default);
}
