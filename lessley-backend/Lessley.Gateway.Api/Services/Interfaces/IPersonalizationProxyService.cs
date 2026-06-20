namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IPersonalizationProxyService
{
    Task<HttpResponseMessage> GetAccountsAsync(string email, CancellationToken ct = default);
    Task<HttpResponseMessage> GetTransactionsAsync(string email, int? days = null, CancellationToken ct = default);
    Task<HttpResponseMessage> GetTransactionsByAccountAsync(string email, string accountId, int? days = null, CancellationToken ct = default);
    Task<HttpResponseMessage> GetClubCategoriesAsync(string clubId, CancellationToken ct = default);

    // Insight endpoints: timeFilter and useMock are hardcoded (true / false) — only days is configurable.
    Task<HttpResponseMessage> GetInsightsCategoriesAsync(string email, int? days = null, CancellationToken ct = default);
    Task<HttpResponseMessage> GetInsightsTopAccountsAsync(string email, int? days = null, CancellationToken ct = default);
    Task<HttpResponseMessage> GetInsightsTopStoresAsync(string email, int? days = null, CancellationToken ct = default);
}
