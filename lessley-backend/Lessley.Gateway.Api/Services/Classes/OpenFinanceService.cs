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
        private readonly IPersonalizationService _personalizationService;
        private readonly ILogger<OpenFinanceService> _logger;

        public OpenFinanceService(
            HttpClient httpClient,
            IConfiguration configuration,
            IPersonalizationService personalizationService,
            ILogger<OpenFinanceService> logger)
        {
            _httpClient = httpClient;
            _configuration = configuration;
            _personalizationService = personalizationService;
            _logger = logger;
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

            if (res is null)
                throw new InvalidOperationException("Failed to generate connect URL.");

            // Triggered here rather than in the controllers so both entry points are covered and
            // a third cannot forget. Note the timing: this fires as the journey *starts*, not
            // when consent lands. For a user who already holds Open Finance consent — most of
            // ours — their history is available right now and this is exact. For a genuinely new
            // link the data arrives later and the next trigger picks it up; the alternative is a
            // provider callback the Gateway does not have.
            await _personalizationService.TriggerCalculateUserCategoriesAsync(username);

            return res;
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

            // It has to be an absolute http(s) URL with a host. Three ways that quietly fails:
            // the setting is missing entirely; DOMAIN was empty when compose expanded
            // "https://${DOMAIN}/insights" into "https:///insights"; or someone put a bare path
            // here. All three end with the user stranded on the provider's site, which is the
            // bug this setting exists to fix — so none of them may pass without saying so.
            if (!Uri.TryCreate(configured, UriKind.Absolute, out var baseUri)
                || (baseUri.Scheme != Uri.UriSchemeHttp && baseUri.Scheme != Uri.UriSchemeHttps)
                || string.IsNullOrEmpty(baseUri.Host))
            {
                _logger.LogError(
                    "OpenFinanceConfig:RedirectUrl is not an absolute http(s) URL (value: '{Configured}'). " +
                    "The bank-linking journey will not return the user to Lessley.",
                    configured);
                return null;
            }

            if (string.IsNullOrWhiteSpace(requested))
                return baseUri.ToString();

            // "//evil.com" is protocol-relative and would leave the site, so one leading slash only.
            var isSafeRelativePath =
                requested.StartsWith('/') &&
                !requested.StartsWith("//") &&
                Uri.IsWellFormedUriString(requested, UriKind.Relative);

            return isSafeRelativePath ? new Uri(baseUri, requested).ToString() : baseUri.ToString();
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
