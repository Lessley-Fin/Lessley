using Lessley.Gateway.Api.Services.Interfaces;

namespace Lessley.Gateway.Api.Services.Classes;

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
}
