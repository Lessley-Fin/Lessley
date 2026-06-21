namespace Lessley.Gateway.Api.Models.DealSearch;

public record DealSearchQuery(
    List<int>? MccCodes,
    string?    StoreText,
    string?    DealText,
    int        Page     = 1,
    int        PageSize = 20
);
