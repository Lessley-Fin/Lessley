namespace Lessley.Gateway.Api.Models.Interest;

/// <summary>
/// One event as the client posts it. Every field is nullable so a malformed batch fails
/// validation in <c>InterestService</c> with a 400 rather than a model-binding 400 whose
/// message says nothing useful.
/// </summary>
/// <remarks>
/// <c>UserId</c> is deliberately absent: the caller does not get to say who they are.
/// </remarks>
public record InterestEventDto(
    string?   EventId,
    string?   EntityType,
    string?   EntityId,
    string?   Action,
    string?   SessionId,
    string?   Surface,
    int?      Position,
    DateTime? Ts
);

public record InterestEventBatchDto(List<InterestEventDto>? Events);

/// <summary>What the hot endpoint returns: deals with their stores, already ordered.</summary>
public record HotDealsResult(List<DealSearch.DealSearchResult> Items);
