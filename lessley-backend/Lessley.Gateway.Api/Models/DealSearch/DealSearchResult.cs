namespace Lessley.Gateway.Api.Models.DealSearch;

public record DealSearchResult(DealDocument Deal, StoreDocument Store);

public record PagedDealSearchResult(List<DealSearchResult> Items, int Total, int Page, int PageSize);
