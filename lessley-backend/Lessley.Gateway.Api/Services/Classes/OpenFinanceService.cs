using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Services.Interfaces;
using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.Json.Serialization;

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

        public async Task<ConnectionResponse> InitiateConnectionJourney(string username, string? redirectUrl = null)
        {
            var accessToken = await CreateAccessToken(username);

            var payload = new
            {
                includeFakeProviders = true,
                expiryDate = DateTime.UtcNow.AddYears(3).ToString("yyyy-MM-dd"),
                allowBusiness = true,
                redirectUrl = ResolveRedirectUrl(redirectUrl)
            };

            var serializerOptions = new JsonSerializerOptions
            {
                DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
            };

            var request = new HttpRequestMessage(HttpMethod.Post, "v2/connections")
            {
                Content = JsonContent.Create(payload, options: serializerOptions)
            };

            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);

            using var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();

            var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
            var res = await response.Content.ReadFromJsonAsync<ConnectionResponse>(options);

            return res ?? throw new InvalidOperationException("Failed to generate connect URL.");
        }

        /// <summary>
        /// Where Open Finance sends the user's browser once they finish linking a bank.
        /// </summary>
        /// <remarks>
        /// Omitting this strands the user on the provider's site — the journey has no way back,
        /// which is what happened to everyone arriving through the registration wizard.
        ///
        /// The destination comes from configuration rather than the caller: this URL is followed
        /// automatically after a successful bank link, so honouring a caller-supplied absolute URL
        /// would be an open redirect. A relative path is accepted so different entry points can
        /// land on different screens; anything else falls back to the configured page.
        /// </remarks>
        private string? ResolveRedirectUrl(string? requested)
        {
            var configured = _configuration["OpenFinanceConfig:RedirectUrl"];
            if (string.IsNullOrWhiteSpace(configured))
                return null;

            if (string.IsNullOrWhiteSpace(requested))
                return configured;

            // "//evil.com" is protocol-relative and leaves the site, so one leading slash only.
            var isSafeRelativePath =
                requested.StartsWith('/') &&
                !requested.StartsWith("//") &&
                Uri.IsWellFormedUriString(requested, UriKind.Relative);

            if (!isSafeRelativePath)
                return configured;

            return Uri.TryCreate(configured, UriKind.Absolute, out var baseUri)
                ? new Uri(baseUri, requested).ToString()
                : configured;
        }

        public async Task<OBTransactionsResponse> GetTransactions(string username)
        {
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
