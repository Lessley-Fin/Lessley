namespace Lessley.Gateway.Api.Models.DealSearch;

public record DealSearchQuery(
    List<string>? MccCodes,
    string?    StoreText,
    string?    DealText,
    int        Page     = 1,
    int        PageSize = 20,
    /// <summary>
    /// Club ids the results are restricted to. Not bound from the request: the service
    /// fills it from the caller's own selection, so a client cannot widen its own scope.
    /// Null means unrestricted.
    /// </summary>
    List<string>? ClubIds = null
);
