using Lessley.Gateway.Api.Models.DealSearch;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IDealFinderService
{
    Task<UserOperationResult> SearchAsync(DealSearchQuery query, CancellationToken ct = default);
    Task<UserOperationResult> GetByIdAsync(string dealId, CancellationToken ct = default);

    /// <summary>Deals ranked by interest, with an exploration slice and a newest-first fallback.</summary>
    Task<UserOperationResult> GetHotAsync(int limit, CancellationToken ct = default);
}
