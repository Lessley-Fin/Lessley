using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Services.Interfaces;
using System.Net.Http.Headers;
using System.Text.Json;

namespace Lessley.Gateway.Api.Services.Classes
{
    public class OpenFinanceService : IOpenFinanceService
    {
        private readonly HttpClient _httpClient;
        private readonly IConfiguration _configuration;

        public OpenFinanceService(HttpClient httpClient, IConfiguration configuration)
        {
            _httpClient = httpClient;
            _configuration = configuration;
        }

        public async Task<string> CreateAccessToken(string username)
        {
            var clientId = _configuration["OpenFinanceConfig:ClientId"];
            var clientSecret = _configuration["OpenFinanceConfig:ClientSecret"];

            var payload = new
            {
                userId = username,
                clientId,
                clientSecret
            };

            using var response = await _httpClient.PostAsJsonAsync("oauth/token", payload);
            response.EnsureSuccessStatusCode();

            var options = new JsonSerializerOptions() { PropertyNameCaseInsensitive = true };
            var res = await response.Content.ReadFromJsonAsync<AccessTokenResponse>(options);
            return res?.AccessToken ?? throw new InvalidOperationException("Failed to extract the access token from the API response.");
        }

        public async Task<ConnectionResponse> InitiateConnectionJourney(string username, string expiryDate)
        {
            var accessToken = await CreateAccessToken(username);

            var payload = new
            {
                includeFakeProviders = true,
                expiryDate
            };

            var request = new HttpRequestMessage(HttpMethod.Post, "v2/connections")
            {
                Content = JsonContent.Create(payload)
            };

            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);

            using var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();

            var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
            var res = await response.Content.ReadFromJsonAsync<ConnectionResponse>(options);

            return res ?? throw new InvalidOperationException("Failed to generate connect URL.");
        }

        public async Task<OBTransactionsResponse> GetTransactions(string username)
        {
            var clientId = _configuration["OpenFinanceConfig:ClientId"];
            var clientSecret = _configuration["OpenFinanceConfig:ClientSecret"];

            var payload = new
            {
                userId = username,
                clientId,
                clientSecret
            };

            var accessToken = await CreateAccessToken(username);

            var request = new HttpRequestMessage(HttpMethod.Get, "v2/data/transactions");

            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
            
            using var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();

            var options = new JsonSerializerOptions() { PropertyNameCaseInsensitive = true };
            var res = await response.Content.ReadFromJsonAsync<OBTransactionsResponse>(options);
            return res ?? throw new InvalidOperationException("Failed to extract the access token from the API response.");
        }
    }
}
