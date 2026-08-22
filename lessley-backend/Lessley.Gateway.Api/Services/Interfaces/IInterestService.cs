using Lessley.Gateway.Api.Models.Interest;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IInterestService
{
    /// <summary>
    /// Validates and stores a client batch of engagement events. <paramref name="callerEmail"/>
    /// becomes every event's <c>user_id</c>, whatever the body claimed.
    /// </summary>
    Task<UserOperationResult> RecordAsync(InterestEventBatchDto batch, string callerEmail, CancellationToken ct = default);

    /// <summary>
    /// Collapses the event window into <c>entity_stats</c> and prunes stats for entities that
    /// have left the catalog. Driven by the nightly job; safe to run at any time.
    /// </summary>
    Task RollupAsync(CancellationToken ct = default);
}
