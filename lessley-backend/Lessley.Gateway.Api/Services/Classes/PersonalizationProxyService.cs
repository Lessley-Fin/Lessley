using Lessley.Gateway.Api.Services.Interfaces;

namespace Lessley.Gateway.Api.Services.Classes;

public class PersonalizationProxyService : IPersonalizationProxyService
{
    private const bool TimeFilter = true;
    private const bool UseMock    = false;

    private readonly HttpClient _httpClient;

    public PersonalizationProxyService(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    public Task<HttpResponseMessage> GetAccountsAsync(string email, CancellationToken ct = default)
        => _httpClient.GetAsync($"open-finance/accounts?email={Uri.EscapeDataString(email)}", ct);

    public Task<HttpResponseMessage> GetTransactionsAsync(
        string email, bool? timeFilter = null, int? days = null, CancellationToken ct = default)
    {
        var url = $"open-finance/transactions?email={Uri.EscapeDataString(email)}";
        if (timeFilter.HasValue) url += $"&time_filter={timeFilter.Value.ToString().ToLower()}";
        if (days.HasValue)       url += $"&days={days.Value}";
        return _httpClient.GetAsync(url, ct);
    }

    public Task<HttpResponseMessage> GetTransactionsByAccountAsync(
        string email, string accountId, bool? timeFilter = null, int? days = null, CancellationToken ct = default)
    {
        var url = $"open-finance/transactions/by-account?email={Uri.EscapeDataString(email)}&account_id={Uri.EscapeDataString(accountId)}";
        if (timeFilter.HasValue) url += $"&time_filter={timeFilter.Value.ToString().ToLower()}";
        if (days.HasValue)       url += $"&days={days.Value}";
        return _httpClient.GetAsync(url, ct);
    }

    public Task<HttpResponseMessage> GetClubCategoriesAsync(string clubId, CancellationToken ct = default)
        => _httpClient.PostAsJsonAsync("clubs/categories", new { club_id = clubId }, ct);

    public Task<HttpResponseMessage> GetInsightsCategoriesAsync(string email, int? days = null, CancellationToken ct = default)
        => _httpClient.GetAsync(BuildInsightsUrl("insights/categories", email, days), ct);

    public Task<HttpResponseMessage> GetInsightsTopAccountsAsync(string email, int? days = null, CancellationToken ct = default)
        => _httpClient.GetAsync(BuildInsightsUrl("insights/top-accounts", email, days), ct);

    public Task<HttpResponseMessage> GetInsightsTopStoresAsync(string email, int? days = null, CancellationToken ct = default)
        => _httpClient.GetAsync(BuildInsightsUrl("insights/top-stores", email, days), ct);

    private static string BuildInsightsUrl(string path, string email, int? days)
    {
        var url = $"{path}?email={Uri.EscapeDataString(email)}&time_filter={TimeFilter.ToString().ToLower()}&use_mock={UseMock.ToString().ToLower()}";
        if (days.HasValue) url += $"&days={days.Value}";
        return url;
    }
}
