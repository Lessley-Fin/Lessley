using Lessley.Gateway.Api.Services.Interfaces;

namespace Lessley.Gateway.Api.Services.Classes;

/// <summary>
/// HTTP proxy to the Personalization (FastAPI) service. All communication is HTTP only
/// (no RabbitMQ yet). Read-only calls return the raw JSON body so the Gateway can pass the
/// Personalization response straight through to the client.
/// </summary>
public class PersonalizationService : IPersonalizationService
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<PersonalizationService> _logger;

    public PersonalizationService(HttpClient httpClient, ILogger<PersonalizationService> logger)
    {
        _httpClient = httpClient;
        _logger     = logger;
    }

    public async Task RecalculateCategoriesAsync(string email, CancellationToken ct = default)
    {
        // Personalization computes + trims categories by match level, then posts the new tags
        // back to the Gateway (PUT /api/user/{email}/tags), which updates DB + SignalR groups.
        var path = $"insights/categories?email={Uri.EscapeDataString(email)}";
        _logger.LogInformation("Triggering category recalculation for {Email}", email);

        using var response = await _httpClient.GetAsync(path, ct);
        response.EnsureSuccessStatusCode();
    }

    public Task RequestClubRecommendationsAsync(string email, CancellationToken ct = default)
    {
        // Fire-and-forget so the Gateway can acknowledge the client immediately. Personalization
        // computes the recommendations and posts a notification back via the user-notification
        // callback (POST /api/notification/user/{email}) on completion.
        var path = $"recommendations/matching-clubs?email={Uri.EscapeDataString(email)}";
        _ = Task.Run(async () =>
        {
            try
            {
                using var response = await _httpClient.GetAsync(path, CancellationToken.None);
                response.EnsureSuccessStatusCode();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Async club recommendation request failed for {Email}", email);
            }
        }, CancellationToken.None);

        return Task.CompletedTask;
    }

    public Task<string> GetPreferredAccountsAsync(string email, CancellationToken ct = default)
        => GetRawAsync($"insights/top-accounts?email={Uri.EscapeDataString(email)}", ct);

    public Task<string> GetPreferredStoresAsync(string email, CancellationToken ct = default)
        => GetRawAsync($"insights/top-stores?email={Uri.EscapeDataString(email)}", ct);

    public Task<string> GetAlternativeStoresAsync(string email, CancellationToken ct = default)
        => GetRawAsync($"insights/missed-savings?email={Uri.EscapeDataString(email)}", ct);

    public Task<string> GetTransactionBreakdownByMccAsync(string email, CancellationToken ct = default)
        => GetRawAsync($"insights/categories?email={Uri.EscapeDataString(email)}", ct);

    private async Task<string> GetRawAsync(string path, CancellationToken ct)
    {
        using var response = await _httpClient.GetAsync(path, ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsStringAsync(ct);
    }
}
