using Lessley.Gateway.Api.Models.Interest;
using Lessley.Gateway.Api.Services.Interfaces;

namespace Lessley.Gateway.Api.Services.Classes;

public class InterestService : IInterestService
{
    /// <summary>
    /// Batch ceiling. The client flushes on a 5s timer with a capped buffer, so a legitimate
    /// batch is small; anything larger is a bug or an attempt to bulk-load the ranking.
    /// </summary>
    public const int MaxBatchSize = 50;

    /// <summary>
    /// How far a client timestamp may lag before it is clamped. Wide enough to survive a
    /// backgrounded tab flushing on <c>visibilitychange</c>, narrow enough that a forged
    /// timestamp cannot buy decay weight it did not earn.
    /// </summary>
    public static readonly TimeSpan MaxClientClockLag = TimeSpan.FromHours(1);

    /// <summary>How much history the rollup scores over — the same window the TTL keeps.</summary>
    public static readonly TimeSpan ScoringWindow = TimeSpan.FromDays(30);

    private readonly IInterestRepository   _interestRepository;
    private readonly IDealFinderRepository _dealRepository;
    private readonly ILogger<InterestService> _logger;

    public InterestService(
        IInterestRepository   interestRepository,
        IDealFinderRepository dealRepository,
        ILogger<InterestService> logger)
    {
        _interestRepository = interestRepository;
        _dealRepository     = dealRepository;
        _logger             = logger;
    }

    public async Task<UserOperationResult> RecordAsync(
        InterestEventBatchDto batch, string callerEmail, CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(callerEmail))
            return UserOperationResult.Forbidden();

        var events = batch.Events;
        if (events is null || events.Count == 0)
            return UserOperationResult.BadRequest(new { error = "At least one event is required." });

        if (events.Count > MaxBatchSize)
            return UserOperationResult.BadRequest(new { error = $"At most {MaxBatchSize} events per batch." });

        var now      = DateTime.UtcNow;
        var earliest = now - MaxClientClockLag;
        var documents = new List<InterestEvent>(events.Count);

        foreach (var dto in events)
        {
            if (string.IsNullOrWhiteSpace(dto.EventId))
                return UserOperationResult.BadRequest(new { error = "eventId is required on every event." });

            if (string.IsNullOrWhiteSpace(dto.EntityId))
                return UserOperationResult.BadRequest(new { error = "entityId is required on every event." });

            if (dto.EntityType is null || !InterestEntityTypes.All.Contains(dto.EntityType))
                return UserOperationResult.BadRequest(new { error = $"Unknown entityType '{dto.EntityType}'." });

            if (dto.Action is null || !InterestActions.All.Contains(dto.Action))
                return UserOperationResult.BadRequest(new { error = $"Unknown action '{dto.Action}'." });

            documents.Add(new InterestEvent
            {
                EventId    = dto.EventId,
                EntityType = dto.EntityType,
                EntityId   = dto.EntityId,
                Action     = dto.Action,
                // The caller does not get to say who they are: whatever the body carried is
                // replaced by the identity the JWT proved.
                UserId     = callerEmail,
                SessionId  = dto.SessionId ?? "",
                Surface    = dto.Surface   ?? "",
                Position   = dto.Position is >= 0 ? dto.Position : null,
                // Clamped rather than rejected — a device with a skewed clock should still be
                // counted, just not be able to place events outside the window.
                Ts         = Clamp(dto.Ts?.ToUniversalTime() ?? now, earliest, now),
            });
        }

        var inserted = await _interestRepository.InsertManyIgnoringDuplicatesAsync(documents, ct);

        return UserOperationResult.Ok(new { accepted = documents.Count, stored = inserted });
    }

    public async Task RollupAsync(CancellationToken ct = default)
    {
        var windowEnd = DateTime.UtcNow;
        var since     = windowEnd - ScoringWindow;

        var triples = await _interestRepository.CollapseTriplesAsync(since, ct);
        var scores  = HotScoreCalculator.Score(triples, windowEnd);

        await _interestRepository.WriteStatsAsync(scores, windowEnd, ct);

        // Prune last: a stat row whose deal has left the catalog would otherwise keep a rank
        // forever, because nothing re-scores an entity that produces no events.
        var dealIds  = await _dealRepository.AllDealIdsAsync(ct);
        var storeIds = await _dealRepository.AllStoreIdsAsync(ct);

        var prunedDeals  = await _interestRepository.DeleteStatsForMissingEntitiesAsync(InterestEntityTypes.Deal,  dealIds,  ct);
        var prunedStores = await _interestRepository.DeleteStatsForMissingEntitiesAsync(InterestEntityTypes.Store, storeIds, ct);

        _logger.LogInformation(
            "Hot-score rollup scored {Entities} entit(ies) from {Triples} triple(s); pruned {PrunedDeals} deal and {PrunedStores} store stat row(s)",
            scores.Count, triples.Count, prunedDeals, prunedStores);
    }

    private static DateTime Clamp(DateTime value, DateTime min, DateTime max) =>
        value < min ? min : value > max ? max : value;
}
