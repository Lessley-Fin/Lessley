using Lessley.Gateway.Api.Models.DealSearch;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IDealFinderRepository
{
    Task<(List<DealSearchResult> Results, int Total)> SearchAsync(DealSearchQuery query, CancellationToken ct = default);
}
