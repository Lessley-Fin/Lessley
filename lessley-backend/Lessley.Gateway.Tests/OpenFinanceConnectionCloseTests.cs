using System.Net;
using System.Text;
using System.Text.Json;
using Lessley.Gateway.Api.Services.Classes;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Xunit;

namespace Lessley.Gateway.Tests;

/// <summary>
/// Revoking a user's bank consent on account deletion.
///
/// Nothing inside Lessley can tell a revoke that never reached the provider from one that did:
/// the account disappears either way and the consent quietly lives on. So these assert on the
/// requests actually leaving the process — method, absolute URL and bearer token — rather than
/// on the service returning without throwing.
/// </summary>
public class OpenFinanceConnectionCloseTests
{
    /// <summary>Answers the token and connection calls, recording every request that was sent.</summary>
    private sealed class RecordingHandler : HttpMessageHandler
    {
        private readonly string _connectionsBody;
        private readonly Func<string, HttpStatusCode> _deleteStatus;

        public RecordingHandler(
            string connectionsBody,
            Func<string, HttpStatusCode>? deleteStatus = null)
        {
            _connectionsBody = connectionsBody;
            _deleteStatus    = deleteStatus ?? (_ => HttpStatusCode.NoContent);
        }

        public List<HttpRequestMessage> Requests { get; } = new();

        public HttpRequestMessage TokenRequest => Requests.Single(r => r.RequestUri!.AbsolutePath.EndsWith("oauth/token"));
        public HttpRequestMessage ListRequest  => Requests.Single(r => r.Method == HttpMethod.Get);
        public List<HttpRequestMessage> DeleteRequests => Requests.Where(r => r.Method == HttpMethod.Delete).ToList();

        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request, CancellationToken cancellationToken)
        {
            Requests.Add(request);

            if (request.RequestUri!.AbsolutePath.EndsWith("oauth/token"))
                return Task.FromResult(Json("""{"accessToken":"token-123"}"""));

            if (request.Method == HttpMethod.Delete)
                return Task.FromResult(new HttpResponseMessage(_deleteStatus(request.RequestUri!.AbsolutePath)));

            return Task.FromResult(Json(_connectionsBody));
        }

        private static HttpResponseMessage Json(string body) => new(HttpStatusCode.OK)
        {
            Content = new StringContent(body, Encoding.UTF8, "application/json"),
        };
    }

    // The value that actually ships — appsettings.json, with no trailing slash and no path.
    // Relative request URIs have to resolve against it correctly or every call 404s.
    private const string BaseUrl = "https://api.open-finance.ai";

    private static (OpenFinanceService Service, RecordingHandler Handler) Build(
        string connectionsBody,
        Func<string, HttpStatusCode>? deleteStatus = null,
        string baseUrl = BaseUrl)
    {
        var handler = new RecordingHandler(connectionsBody, deleteStatus);
        var http    = new HttpClient(handler) { BaseAddress = new Uri(baseUrl) };

        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["OpenFinanceConfig:ClientId"]     = "id",
                ["OpenFinanceConfig:ClientSecret"] = "secret",
            })
            .Build();

        var service = new OpenFinanceService(
            http,
            configuration,
            Mock.Of<IPersonalizationService>(),
            NullLogger<OpenFinanceService>.Instance);

        return (service, handler);
    }

    [Fact]
    public async Task CloseAllConnections_SendsDeleteToTheConnectionUrlWithTheUsersBearerToken()
    {
        var (service, handler) = Build("""{"items":[{"id":"conn-1"},{"id":"conn-2"}]}""");

        await service.CloseAllConnectionsAsync("user@test.com");

        // The token is minted for this user — it is what scopes the listing and the deletes.
        var tokenBody = JsonDocument.Parse(await handler.TokenRequest.Content!.ReadAsStringAsync()).RootElement;
        Assert.Equal("user@test.com", tokenBody.GetProperty("userId").GetString());
        Assert.Equal("id",            tokenBody.GetProperty("clientId").GetString());
        Assert.Equal("secret",        tokenBody.GetProperty("clientSecret").GetString());

        Assert.Equal("https://api.open-finance.ai/v2/connections", handler.ListRequest.RequestUri!.ToString());
        Assert.Equal("Bearer",    handler.ListRequest.Headers.Authorization!.Scheme);
        Assert.Equal("token-123", handler.ListRequest.Headers.Authorization!.Parameter);

        Assert.Equal(
            new[]
            {
                "https://api.open-finance.ai/v2/connections/conn-1",
                "https://api.open-finance.ai/v2/connections/conn-2",
            },
            handler.DeleteRequests.Select(r => r.RequestUri!.ToString()));

        Assert.All(handler.DeleteRequests, r =>
        {
            Assert.Equal("Bearer",    r.Headers.Authorization!.Scheme);
            Assert.Equal("token-123", r.Headers.Authorization!.Parameter);
        });

        // One token for the whole run, not one per connection.
        Assert.Single(handler.Requests, r => r.RequestUri!.AbsolutePath.EndsWith("oauth/token"));
    }

    [Fact]
    public async Task CloseAllConnections_ReadsTheIdUnderEitherSpelling()
    {
        // The creation response calls it connectionId; collections usually return plain id.
        var (service, handler) = Build("""{"items":[{"connectionId":"conn-a"},{"id":"conn-b"}]}""");

        await service.CloseAllConnectionsAsync("user@test.com");

        Assert.Equal(
            new[] { "/v2/connections/conn-a", "/v2/connections/conn-b" },
            handler.DeleteRequests.Select(r => r.RequestUri!.AbsolutePath));
    }

    [Fact]
    public async Task CloseAllConnections_NoConnections_SendsNoDeletes()
    {
        var (service, handler) = Build("""{"items":[]}""");

        await service.CloseAllConnectionsAsync("user@test.com");

        Assert.Empty(handler.DeleteRequests);
    }

    [Fact]
    public async Task CloseAllConnections_AlreadyGone_IsTreatedAsClosed()
    {
        // Idempotent on purpose: a retry after a partial run must not be blocked by the
        // connections the first run already closed.
        var (service, handler) = Build(
            """{"items":[{"id":"conn-1"},{"id":"conn-2"}]}""",
            deleteStatus: path => path.EndsWith("conn-1") ? HttpStatusCode.NotFound : HttpStatusCode.NoContent);

        await service.CloseAllConnectionsAsync("user@test.com");

        Assert.Equal(2, handler.DeleteRequests.Count);
    }

    [Fact]
    public async Task CloseAllConnections_ProviderRefusesTheDelete_Throws()
    {
        // The throw is what makes the caller abort the account deletion instead of orphaning
        // a live consent.
        var (service, _) = Build(
            """{"items":[{"id":"conn-1"}]}""",
            deleteStatus: _ => HttpStatusCode.InternalServerError);

        await Assert.ThrowsAsync<HttpRequestException>(
            () => service.CloseAllConnectionsAsync("user@test.com"));
    }

    [Fact]
    public async Task CloseAllConnections_ListingFails_Throws()
    {
        var handler = new ThrowingListHandler();
        var http    = new HttpClient(handler) { BaseAddress = new Uri(BaseUrl) };
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["OpenFinanceConfig:ClientId"]     = "id",
                ["OpenFinanceConfig:ClientSecret"] = "secret",
            })
            .Build();

        var service = new OpenFinanceService(
            http, configuration, Mock.Of<IPersonalizationService>(),
            NullLogger<OpenFinanceService>.Instance);

        await Assert.ThrowsAsync<HttpRequestException>(
            () => service.CloseAllConnectionsAsync("user@test.com"));
    }

    private sealed class ThrowingListHandler : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request, CancellationToken cancellationToken)
            => Task.FromResult(request.RequestUri!.AbsolutePath.EndsWith("oauth/token")
                ? new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent("""{"accessToken":"token-123"}""", Encoding.UTF8, "application/json"),
                }
                : new HttpResponseMessage(HttpStatusCode.ServiceUnavailable));
    }

    [Fact]
    public async Task GetConnectionIds_ReturnsTheIdsAndSkipsEntriesWithNone()
    {
        var (service, _) = Build("""{"items":[{"id":"conn-1"},{"other":"noise"},{"id":""}]}""");

        var ids = await service.GetConnectionIdsAsync("user@test.com");

        Assert.Equal(new[] { "conn-1" }, ids);
    }
}
