using Lessley.Gateway.Api.Models.Interest;
using Lessley.Gateway.Api.Services.Classes;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IInterestRepository
{
    /// <summary>
    /// Inserts a batch, treating duplicate <c>event_id</c>s as success. Returns how many rows
    /// were new.
    /// </summary>
    Task<int> InsertManyIgnoringDuplicatesAsync(IReadOnlyList<InterestEvent> events, CancellationToken ct = default);

    /// <summary>Records one more empty-result search for a normalized query.</summary>
    Task UpsertSearchGapAsync(string queryNorm, CancellationToken ct = default);

    /// <summary>Entity ids of the highest-scoring rows, best first.</summary>
    Task<List<string>> TopByScoreAsync(string entityType, int limit, CancellationToken ct = default);

    /// <summary>
    /// Entity ids the ranking already knows enough about — i.e. seen by at least
    /// <paramref name="minImpressions"/> distinct users. Exploration draws from everything else.
    /// </summary>
    Task<HashSet<string>> WellObservedEntityIdsAsync(string entityType, int minImpressions, CancellationToken ct = default);

    // ── Rollup read/write pair ────────────────────────────────────────────────

    /// <summary>
    /// Collapses raw events newer than <paramref name="since"/> to distinct
    /// <c>(entity, user, action)</c> triples carrying their newest timestamp.
    /// </summary>
    Task<List<InterestTriple>> CollapseTriplesAsync(DateTime since, CancellationToken ct = default);

    /// <summary>Upserts scored rows, keyed on <c>(entity_type, entity_id)</c>.</summary>
    Task WriteStatsAsync(IReadOnlyList<EntityScore> scores, DateTime windowEnd, CancellationToken ct = default);

    /// <summary>
    /// Drops stats for entities that no longer exist in the catalog, so a de-listed deal
    /// cannot keep a rank.
    /// </summary>
    Task<long> DeleteStatsForMissingEntitiesAsync(string entityType, IReadOnlyCollection<string> existingIds, CancellationToken ct = default);
}
