using Lessley.Gateway.Api.Models.DealSearch;
using Lessley.Gateway.Api.Models.Interest;
using Lessley.Gateway.Api.Services.Interfaces;
using System.Security.Cryptography;

namespace Lessley.Gateway.Api.Services.Classes;

public class DealFinderService : IDealFinderService
{
    /// <summary>Share of the hot list reserved for under-observed deals, as a divisor: 5 → ~20%.</summary>
    private const int ExplorationDivisor = 5;

    /// <summary>Distinct viewers above which a deal is no longer an exploration candidate.</summary>
    private const int WellObservedImpressions = 50;

    /// <summary>How far back exploration will reach for a candidate.</summary>
    private static readonly TimeSpan ExplorationFreshness = TimeSpan.FromDays(30);

    private readonly IDealFinderRepository _repository;
    private readonly IInterestRepository   _interestRepository;

    public DealFinderService(IDealFinderRepository repository, IInterestRepository interestRepository)
    {
        _repository         = repository;
        _interestRepository = interestRepository;
    }

    public async Task<UserOperationResult> GetByIdAsync(string dealId, CancellationToken ct = default)
    {
        var result = await _repository.GetByIdAsync(dealId, ct);
        return result is null
            ? UserOperationResult.NotFound()
            : UserOperationResult.Ok(result);
    }

    public async Task<UserOperationResult> SearchAsync(DealSearchQuery query, CancellationToken ct = default)
    {
        if ((query.MccCodes is null || query.MccCodes.Count == 0)
            && string.IsNullOrWhiteSpace(query.StoreText)
            && string.IsNullOrWhiteSpace(query.DealText))
            return UserOperationResult.BadRequest(new { error = "At least one filter (mccs, store, deal) is required." });

        var page     = Math.Max(1, query.Page);
        var pageSize = Math.Clamp(query.PageSize, 1, 100);
        var normalized = query with { Page = page, PageSize = pageSize };

        var (results, total) = await _repository.SearchAsync(normalized, ct);

        // A text search that found nothing is the one signal that says what the catalog is
        // missing, so it is recorded on the way out. Unjoinable to a user by design — see
        // SearchGap. Failures are swallowed: a telemetry write must never fail a search.
        if (total == 0)
            await RecordSearchGapAsync(query, ct);

        return UserOperationResult.Ok(new PagedDealSearchResult(results, total, page, pageSize));
    }

    /// <summary>
    /// The hot feed: ranked deals, topped up with newest-first deals until the ranking has
    /// data, plus a reserved slice of randomly chosen under-observed deals.
    /// </summary>
    /// <remarks>
    /// The exploration slice is not a nicety. Impressions are only earned by being shown, so a
    /// ranking that only ever shows its own top results learns nothing about anything else and
    /// whatever led on day one leads forever. Reserving ~20% of the list for deals the ranking
    /// has barely seen is what keeps the feed able to change its mind.
    ///
    /// The <c>RecentlyScrapedAsync</c> top-up is what lets this ship before a single event
    /// exists: on an empty <c>entity_stats</c> the endpoint degrades to newest-first, and it
    /// becomes a real ranking as rows appear — no code change, no backfill.
    /// </remarks>
    public async Task<UserOperationResult> GetHotAsync(int limit, CancellationToken ct = default)
    {
        limit = Math.Clamp(limit, 1, 50);

        var exploreCount = Math.Max(1, limit / ExplorationDivisor);
        var rankedCount  = limit - exploreCount;

        var rankedIds = await _interestRepository.TopByScoreAsync(InterestEntityTypes.Deal, rankedCount, ct);
        var ranked    = await _repository.GetByIdsAsync(rankedIds, ct);

        // Ids, not results: a ranked id whose deal or store row has since disappeared must
        // still be excluded from the top-up, or the fallback would re-suggest a broken deal.
        var chosen = new HashSet<string>(rankedIds);

        if (ranked.Count < rankedCount)
        {
            var fallback = await _repository.RecentlyScrapedAsync(rankedCount - ranked.Count, chosen, ct);
            ranked.AddRange(fallback);
            foreach (var item in fallback) chosen.Add(item.Deal.DealId);
        }

        var wellObserved = await _interestRepository.WellObservedEntityIdsAsync(
            InterestEntityTypes.Deal, WellObservedImpressions, ct);
        wellObserved.UnionWith(chosen);

        var explore = await _repository.RandomDealsAsync(
            exploreCount, DateTime.UtcNow - ExplorationFreshness, wellObserved, ct);

        // Shuffled so the exploration slots do not become a stable secondary ranking of their
        // own — $sample already randomizes selection, this randomizes placement.
        var items = ranked.Concat(Shuffle(explore)).ToList();

        return UserOperationResult.Ok(new HotDealsResult(items));
    }

    private async Task RecordSearchGapAsync(DealSearchQuery query, CancellationToken ct)
    {
        var text = string.Join(' ', new[] { query.StoreText, query.DealText }
            .Where(t => !string.IsNullOrWhiteSpace(t)));

        var normalized = NormalizeQuery(text);
        if (normalized.Length == 0) return;

        try
        {
            await _interestRepository.UpsertSearchGapAsync(normalized, ct);
        }
        catch (Exception) when (!ct.IsCancellationRequested)
        {
            // Intentionally silent: the user asked for deals, not for their miss to be logged.
        }
    }

    /// <summary>Lowercased, trimmed, whitespace collapsed — so "  Zara   Home " and "zara home" are one gap.</summary>
    internal static string NormalizeQuery(string? text) =>
        string.Join(' ', (text ?? "").Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries))
              .ToLowerInvariant();

    private static List<T> Shuffle<T>(List<T> items)
    {
        for (var i = items.Count - 1; i > 0; i--)
        {
            var j = RandomNumberGenerator.GetInt32(i + 1);
            (items[i], items[j]) = (items[j], items[i]);
        }
        return items;
    }
}
