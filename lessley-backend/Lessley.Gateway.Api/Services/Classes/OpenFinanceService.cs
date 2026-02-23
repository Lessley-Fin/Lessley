using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Services.Interfaces;
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
    }
}
