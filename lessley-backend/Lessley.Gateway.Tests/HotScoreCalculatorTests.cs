using Lessley.Gateway.Api.Models.Interest;
using Lessley.Gateway.Api.Services.Classes;
using Xunit;

namespace Lessley.Gateway.Tests;

/// <summary>
/// The hot-score math. Deliberately infrastructure-free — the scoring is the part of the
/// ranking that can actually be wrong in a way nobody notices, so it has to be cheap to assert.
/// </summary>
public class HotScoreCalculatorTests
{
    private static readonly DateTime Now = new(2026, 8, 22, 12, 0, 0, DateTimeKind.Utc);

    /// <summary>Builds <paramref name="count"/> distinct actors doing <paramref name="action"/>.</summary>
    private static IEnumerable<InterestTriple> Actors(
        string entityId, string action, int count, DateTime? ts = null, int userOffset = 0) =>
        Enumerable.Range(userOffset, count).Select(i => new InterestTriple(
            InterestEntityTypes.Deal, entityId, $"user{i}@test.com", action, ts ?? Now));

    private static double ScoreOf(List<EntityScore> scores, string entityId) =>
        scores.Single(s => s.EntityId == entityId).HotScore;

    [Fact]
    public void HighRateLowVolume_OutranksLowRateHighVolume()
    {
        // A: 8 of 10 viewers clicked through. B: 6 of 300 did, on 30× the exposure.
        var triples = Actors("deal-a", InterestActions.Impression, 10)
            .Concat(Actors("deal-a", InterestActions.Redirect, 8))
            .Concat(Actors("deal-b", InterestActions.Impression, 300, userOffset: 1000))
            .Concat(Actors("deal-b", InterestActions.Redirect, 6, userOffset: 1000))
            .ToList();

        var scores = HotScoreCalculator.Score(triples, Now);

        Assert.True(ScoreOf(scores, "deal-a") > ScoreOf(scores, "deal-b"),
            "a deal most viewers acted on must beat one most viewers ignored, however often it was shown");
    }

    [Fact]
    public void OneUsersRepeatedRedirect_CountsOnce()
    {
        // What the collapse to distinct triples buys: fifty redirects from one person arrive
        // as one triple and therefore score exactly as one person's interest.
        var single = new List<InterestTriple>
        {
            new(InterestEntityTypes.Deal, "deal-a", "spammer@test.com", InterestActions.Impression, Now),
            new(InterestEntityTypes.Deal, "deal-a", "spammer@test.com", InterestActions.Redirect,   Now),
        };

        var scores = HotScoreCalculator.Score(single, Now);
        var row    = scores.Single();

        Assert.Equal(1, row.Impressions);
        Assert.Equal(1, row.Actors);

        // Two genuine users must outscore one, which is the property spam cannot buy.
        var two = single.Concat(new[]
        {
            new InterestTriple(InterestEntityTypes.Deal, "deal-a", "second@test.com", InterestActions.Impression, Now),
            new InterestTriple(InterestEntityTypes.Deal, "deal-a", "second@test.com", InterestActions.Redirect,   Now),
        }).ToList();

        Assert.True(HotScoreCalculator.Score(two, Now).Single().HotScore > row.HotScore);
    }

    [Fact]
    public void ThirtyDayOldEngagement_ScoresFarBelowFresh()
    {
        var stale = Now.AddDays(-30);

        var triples = Actors("fresh", InterestActions.Impression, 10)
            .Concat(Actors("fresh", InterestActions.Redirect, 5))
            .Concat(Actors("stale", InterestActions.Impression, 10, ts: stale, userOffset: 100))
            .Concat(Actors("stale", InterestActions.Redirect, 5, ts: stale, userOffset: 100))
            .ToList();

        var scores = HotScoreCalculator.Score(triples, Now);

        // Same actors, same rate — only the age differs. Four half-lives is a >10× cut in
        // weight, which the log compresses to roughly a third of the score.
        Assert.True(ScoreOf(scores, "stale") < ScoreOf(scores, "fresh") * 0.5,
            "a month-old burst must not sit alongside this week's");
    }

    [Fact]
    public void StoreEngagement_DoesNotDistortTheDealBaseline()
    {
        // Stores never receive an impression — nothing "shows" a store as itself — so pooling
        // both types into one baseline would divide store engagement by deal impressions and
        // put the mean rate above anything a deal can reach.
        var deals = Actors("deal-a", InterestActions.Impression, 10)
            .Concat(Actors("deal-a", InterestActions.Redirect, 2))
            .ToList();

        var withStores = deals.Concat(Enumerable.Range(0, 40).Select(i => new InterestTriple(
            InterestEntityTypes.Store, "store-a", $"shopper{i}@test.com", InterestActions.Redirect, Now)))
            .ToList();

        var alone   = HotScoreCalculator.Score(deals, Now).Single(s => s.EntityId == "deal-a");
        var mingled = HotScoreCalculator.Score(withStores, Now).Single(s => s.EntityId == "deal-a");

        Assert.Equal(alone.HotScore, mingled.HotScore, 10);
    }

    [Fact]
    public void EmptyInput_ProducesNoRows()
    {
        Assert.Empty(HotScoreCalculator.Score([], Now));
    }

    [Fact]
    public void ImpressionsWithNoEngagementAnywhere_ProduceFiniteZeroScores()
    {
        // The degenerate first day: everything has been seen, nothing has been clicked. The
        // global rate is 0, so every rate is 0 — the danger is NaN, not a tie.
        var triples = Actors("deal-a", InterestActions.Impression, 5).ToList();

        var row = HotScoreCalculator.Score(triples, Now).Single();

        Assert.False(double.IsNaN(row.HotScore));
        Assert.False(double.IsInfinity(row.HotScore));
        Assert.Equal(0d, row.HotScore, 10);
    }

    [Fact]
    public void EngagementWithNoImpressionsAnywhere_StaysFinite()
    {
        // Possible when an IntersectionObserver never fired but a click did. Dividing by
        // (0 + M) is what keeps this finite rather than infinite.
        var triples = Actors("deal-a", InterestActions.CouponCopy, 3).ToList();

        var row = HotScoreCalculator.Score(triples, Now).Single();

        Assert.False(double.IsNaN(row.HotScore));
        Assert.False(double.IsInfinity(row.HotScore));
        Assert.Equal(0, row.Impressions);
        Assert.Equal(3, row.Actors);
    }

    [Fact]
    public void FutureTimestamp_EarnsNoMoreThanNow()
    {
        // The service clamps on ingest; this is the second guard. A client clock running an
        // hour fast must not buy weight a correct clock cannot.
        var now    = HotScoreCalculator.Score(Actors("deal-a", InterestActions.Redirect, 1).ToList(), Now).Single();
        var future = HotScoreCalculator.Score(
            Actors("deal-a", InterestActions.Redirect, 1, ts: Now.AddDays(5)).ToList(), Now).Single();

        Assert.Equal(now.HotScore, future.HotScore, 10);
    }
}
