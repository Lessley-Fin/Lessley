using Lessley.Gateway.Api.Models.DealSearch;
using Lessley.Gateway.Api.Services.Interfaces;

namespace Lessley.Gateway.Api.Services.Classes;

public class DealFinderService : IDealFinderService
{
    private readonly IDealFinderRepository _repository;
    private readonly IUserService          _userService;

    /// <summary>
    /// A loadable card sold at two rates is stored as one club per rate
    /// (<c>club_paisplus_networks_regular</c> / <c>_vip</c>), while a user selects only
    /// the un-suffixed parent the clubs collection holds. Matching the selection
    /// verbatim would drop every tiered deal, so each pick covers its own rungs too.
    /// </summary>
    private static readonly string[] TierSuffixes = ["", "_regular", "_vip"];

    public DealFinderService(IDealFinderRepository repository, IUserService userService)
    {
        _repository  = repository;
        _userService = userService;
    }

    public async Task<UserOperationResult> GetByIdAsync(string dealId, CancellationToken ct = default)
    {
        var result = await _repository.GetByIdAsync(dealId, ct);
        return result is null
            ? UserOperationResult.NotFound()
            : UserOperationResult.Ok(result);
    }

    public async Task<UserOperationResult> SearchAsync(DealSearchQuery query, string callerEmail, CancellationToken ct = default)
    {
        if ((query.MccCodes is null || query.MccCodes.Count == 0)
            && string.IsNullOrWhiteSpace(query.StoreText)
            && string.IsNullOrWhiteSpace(query.DealText))
            return UserOperationResult.BadRequest(new { error = "At least one filter (mccs, store, deal) is required." });

        var page     = Math.Max(1, query.Page);
        var pageSize = Math.Clamp(query.PageSize, 1, 100);

        // Results are scoped to the clubs the caller actually holds — an offer on a card
        // they have no membership in is not a benefit to them. Resolved here rather than
        // taken from the request so a client cannot search outside its own selection.
        //
        // No selection means there is nothing to narrow by, so search stays open: a user
        // who has not picked a club yet should still get results rather than an empty page.
        var selected = await _userService.GetUserClubsAsync(callerEmail, ct);
        var clubIds  = selected is { Count: > 0 } ? ExpandTiers(selected) : null;

        var normalized = query with { Page = page, PageSize = pageSize, ClubIds = clubIds };

        var (results, total) = await _repository.SearchAsync(normalized, ct);

        return UserOperationResult.Ok(new PagedDealSearchResult(results, total, page, pageSize));
    }

    private static List<string> ExpandTiers(List<string> clubIds) =>
        clubIds
            .Where(id => !string.IsNullOrWhiteSpace(id))
            .SelectMany(id => TierSuffixes.Select(suffix => id + suffix))
            .Distinct()
            .ToList();
}
