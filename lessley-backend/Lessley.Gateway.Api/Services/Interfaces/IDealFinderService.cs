using Lessley.Gateway.Api.Models.DealSearch;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IDealFinderService
{
    Task<UserOperationResult> SearchAsync(DealSearchQuery query, CancellationToken ct = default);
}
