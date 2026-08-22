using Lessley.Gateway.Api.Models.Interest;

namespace Lessley.Gateway.Api.Services.Classes;

/// <summary>
/// One distinct <c>(entity, user, action)</c> triple, carrying the newest timestamp the user
/// produced for that action. This is the unit the score is computed over — never raw events.
/// </summary>
/// <remarks>
/// Collapsing to triples before scoring is what makes spam inert by construction: one user
/// copying a coupon fifty times produces exactly one triple, so there is no volume to inflate
/// and no defense to write.
/// </remarks>
public readonly record struct InterestTriple(
    string   EntityType,
    string   EntityId,
    string   UserId,
    string   Action,
    DateTime LatestTs
);

/// <summary>One entity's scored row, ready to be written to <c>entity_stats</c>.</summary>
public readonly record struct EntityScore(
    string EntityType,
    string EntityId,
    double HotScore,
    int    Impressions,
    int    Actors
);

/// <summary>
/// The hot-score math, as a pure function over collapsed triples.
/// </summary>
/// <remarks>
/// Deliberately static and database-free: this is the part of the ranking worth testing, and
/// it must be testable without infrastructure. The rollup job supplies the triples; nothing
/// here knows where they came from.
///
/// <code>
/// impressionActors = distinct users with an impression
/// engageActors     = distinct users with action in {open, coupon_copy, redirect}
/// decayedWeight    = Σ W[action] · 0.5^(ageDays(latestTs) / HalfLifeDays)
/// rate             = (engageActors + M·globalRate) / (impressionActors + M)
/// hotScore         = rate · log(1 + decayedWeight)
/// </code>
///
/// The two factors carry different things on purpose. <c>rate</c> is quality — what share of
/// the people who saw this actually took it — smoothed toward the global mean so a deal shown
/// to three people cannot top the list on one click. <c>log(1 + decayedWeight)</c> is recent
/// volume with sharply diminishing returns, and the half-life is what keeps the feed a *this
/// month* feed rather than an all-time one.
/// </remarks>
public static class HotScoreCalculator
{
    /// <summary>Smoothing strength: how many "average" impressions every entity is credited with.</summary>
    public const double SmoothingM = 30d;

    /// <summary>Days after which an action counts half as much.</summary>
    public const double HalfLifeDays = 7d;

    /// <summary>
    /// What each action is worth in the volume term. An outbound click is worth twelve
    /// impressions because it is the closest thing to intent this pipeline can observe.
    /// </summary>
    public static readonly IReadOnlyDictionary<string, double> ActionWeights =
        new Dictionary<string, double>
        {
            [InterestActions.Impression] = 1d,
            [InterestActions.SearchHit]  = 2d,
            [InterestActions.Open]       = 4d,
            [InterestActions.CouponCopy] = 10d,
            [InterestActions.Redirect]   = 12d,
        };

    /// <summary>
    /// Scores every entity present in <paramref name="triples"/>.
    /// </summary>
    /// <param name="triples">Collapsed distinct triples, in any order.</param>
    /// <param name="now">End of the scoring window; ages are measured back from here.</param>
    public static List<EntityScore> Score(IEnumerable<InterestTriple> triples, DateTime now)
    {
        var byEntity = triples
            .GroupBy(t => (t.EntityType, t.EntityId))
            .ToList();

        if (byEntity.Count == 0) return [];

        // Per-entity actor counts, computed once: the global rate is derived from the same
        // numbers the per-entity rate uses, so a single deal cannot be measured against a
        // baseline it did not contribute to.
        var counted = byEntity
            .Select(group => new
            {
                group.Key.EntityType,
                group.Key.EntityId,
                ImpressionActors = DistinctUsers(group, u => u.Action == InterestActions.Impression),
                EngageActors     = DistinctUsers(group, u => InterestActions.Engagement.Contains(u.Action)),
                Actors           = group.Select(t => t.UserId).Distinct().Count(),
                DecayedWeight    = group.Sum(t => Weight(t.Action) * Decay(t.LatestTs, now)),
            })
            .ToList();

        // One baseline per entity type, not one overall. Impressions are only recorded for
        // deals — a store is never "shown" as itself — so a shared baseline would divide every
        // store's engagement into the deals' impression count and push the mean far above what
        // any deal actually achieves.
        var globalRateByType = counted
            .GroupBy(e => e.EntityType)
            .ToDictionary(g => g.Key, g =>
            {
                var impressionActors = g.Sum(e => (long)e.ImpressionActors);
                // With no impressions there is no baseline to smooth toward. Zero is the honest
                // answer and, critically, keeps `rate` finite — entities of that type then rank
                // purely on volume until impressions start arriving.
                return impressionActors > 0
                    ? (double)g.Sum(e => (long)e.EngageActors) / impressionActors
                    : 0d;
            });

        return counted
            .Select(e =>
            {
                var globalRate = globalRateByType[e.EntityType];
                var rate = (e.EngageActors + SmoothingM * globalRate) / (e.ImpressionActors + SmoothingM);
                return new EntityScore(
                    e.EntityType,
                    e.EntityId,
                    rate * Math.Log(1d + e.DecayedWeight),
                    e.ImpressionActors,
                    e.Actors);
            })
            .ToList();
    }

    private static int DistinctUsers(IEnumerable<InterestTriple> group, Func<InterestTriple, bool> predicate) =>
        group.Where(predicate).Select(t => t.UserId).Distinct().Count();

    private static double Weight(string action) =>
        ActionWeights.TryGetValue(action, out var weight) ? weight : 0d;

    /// <summary>
    /// Half-life decay, clamped at 1 for anything dated in the future — a client clock running
    /// fast must not be able to buy extra weight (the service also clamps timestamps on ingest,
    /// so this is the second of two guards).
    /// </summary>
    private static double Decay(DateTime ts, DateTime now)
    {
        var ageDays = (now - ts).TotalDays;
        return ageDays <= 0 ? 1d : Math.Pow(0.5d, ageDays / HalfLifeDays);
    }
}
