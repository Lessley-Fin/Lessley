namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IPersonalizationProxyService
{
    Task<HttpResponseMessage> GetAccountsAsync(string email, CancellationToken ct = default);
    Task<HttpResponseMessage> GetTransactionsAsync(string email, bool? timeFilter = null, int? days = null, CancellationToken ct = default);
    Task<HttpResponseMessage> GetTransactionsByAccountAsync(string email, string accountId, bool? timeFilter = null, int? days = null, CancellationToken ct = default);
    Task<HttpResponseMessage> GetClubCategoriesAsync(string clubId, CancellationToken ct = default);
    Task<HttpResponseMessage> GetInsightsCategoriesAsync(string email, bool? timeFilter = null, int? days = null, bool? useMock = null, CancellationToken ct = default);
    Task<HttpResponseMessage> GetInsightsTopAccountsAsync(string email, bool? timeFilter = null, int? days = null, bool? useMock = null, CancellationToken ct = default);
    Task<HttpResponseMessage> GetInsightsTopStoresAsync(string email, bool? timeFilter = null, int? days = null, bool? useMock = null, CancellationToken ct = default);
}
