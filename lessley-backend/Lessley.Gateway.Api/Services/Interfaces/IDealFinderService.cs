using Lessley.Gateway.Api.Models.DealSearch;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IDealFinderService
{
    Task<UserOperationResult> GetByIdAsync(string dealId, CancellationToken ct = default);
    Task<UserOperationResult> SearchAsync(DealSearchQuery query, string callerEmail, CancellationToken ct = default);
}
