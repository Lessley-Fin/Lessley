using Lessley.Gateway.Api.Models.DealSearch;
using Lessley.Gateway.Api.Services.Interfaces;

namespace Lessley.Gateway.Api.Services.Classes;

public class DealFinderService : IDealFinderService
{
    private readonly IDealFinderRepository _repository;

    public DealFinderService(IDealFinderRepository repository) => _repository = repository;

    public async Task<UserOperationResult> GetByIdAsync(string dealId, CancellationToken ct = default)
    {
        var result = await _repository.GetByIdAsync(dealId, ct);
        return result is null
            ? UserOperationResult.NotFound()
            : UserOperationResult.Ok(result);
    }

    public async Task<UserOperationResult> SearchAsync(DealSearchQuery query, CancellationToken ct = default)
    {
        if ((query.MccCodes is null || query.MccCodes.Count == 0)
            && string.IsNullOrWhiteSpace(query.StoreText)
            && string.IsNullOrWhiteSpace(query.DealText))
            return UserOperationResult.BadRequest(new { error = "At least one filter (mccs, store, deal) is required." });

        var page     = Math.Max(1, query.Page);
        var pageSize = Math.Clamp(query.PageSize, 1, 100);
        var normalized = query with { Page = page, PageSize = pageSize };

        var (results, total) = await _repository.SearchAsync(normalized, ct);

        return UserOperationResult.Ok(new PagedDealSearchResult(results, total, page, pageSize));
    }
}
