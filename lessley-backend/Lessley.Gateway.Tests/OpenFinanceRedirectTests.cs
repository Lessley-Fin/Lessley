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
/// Where Open Finance sends the user after they link a bank.
///
/// Getting this wrong is invisible from inside Lessley: the connection is created, the API
/// answers 200, and the user simply never comes back — which is exactly what happened before
/// the setting existed. So the assertion is on the JSON actually leaving the process, not on
/// the value the configuration returns.
/// </summary>
public class OpenFinanceRedirectTests
{
    /// <summary>Answers the token and connection calls, keeping the connection request body.</summary>
    private sealed class CapturingHandler : HttpMessageHandler
    {
        public string? ConnectionBody { get; private set; }

        protected override async Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request, CancellationToken cancellationToken)
        {
            var path = request.RequestUri!.AbsolutePath;

            if (path.EndsWith("oauth/token"))
                return Json("""{"accessToken":"token-123"}""");

            ConnectionBody = request.Content is null
                ? null
                : await request.Content.ReadAsStringAsync(cancellationToken);

            return Json("""{"connectUrl":"https://provider.example/journey","connectionId":"conn-1"}""");
        }

        private static HttpResponseMessage Json(string body) => new(HttpStatusCode.OK)
        {
            Content = new StringContent(body, Encoding.UTF8, "application/json"),
        };
    }

    private static async Task<JsonElement> SendJourneyAsync(string? configuredRedirect, string? requested = null)
    {
        var handler = new CapturingHandler();
        var http    = new HttpClient(handler) { BaseAddress = new Uri("https://api.open-finance.test/") };

        var settings = new Dictionary<string, string?>
        {
            ["OpenFinanceConfig:ClientId"]     = "id",
            ["OpenFinanceConfig:ClientSecret"] = "secret",
        };
        if (configuredRedirect is not null)
            settings["OpenFinanceConfig:RedirectUrl"] = configuredRedirect;

        var configuration = new ConfigurationBuilder().AddInMemoryCollection(settings).Build();

        var service = new OpenFinanceService(
            http,
            configuration,
            Mock.Of<IPersonalizationService>(),
            NullLogger<OpenFinanceService>.Instance);

        await service.InitiateConnectionJourney("user@test.com", requested);

        return JsonDocument.Parse(handler.ConnectionBody!).RootElement;
    }

    [Fact]
    public async Task ConfiguredAbsoluteUrl_IsSentToOpenFinance()
    {
        // The value both compose files set: https://${DOMAIN}/insights
        var body = await SendJourneyAsync("https://lessley.example.com/insights");

        Assert.Equal("https://lessley.example.com/insights", body.GetProperty("redirectUrl").GetString());
    }

    [Fact]
    public async Task LocalDefault_IsSentToOpenFinance()
    {
        // appsettings.json's fallback, used when the env var is absent.
        var body = await SendJourneyAsync("http://localhost/insights");

        Assert.Equal("http://localhost/insights", body.GetProperty("redirectUrl").GetString());
    }

    [Fact]
    public async Task ARelativePathFromTheCaller_ResolvesAgainstTheConfiguredOrigin()
    {
        var body = await SendJourneyAsync("https://lessley.example.com/insights", "/settings");

        Assert.Equal("https://lessley.example.com/settings", body.GetProperty("redirectUrl").GetString());
    }

    [Theory]
    [InlineData("https://evil.example.com/steal")]
    [InlineData("//evil.example.com")]
    public async Task AnAbsoluteOrProtocolRelativeUrlFromTheCaller_IsIgnored(string attack)
    {
        // This URL is followed automatically after a successful bank link, so honouring a
        // caller-supplied destination would be an open redirect at the worst possible moment.
        var body = await SendJourneyAsync("https://lessley.example.com/insights", attack);

        Assert.Equal("https://lessley.example.com/insights", body.GetProperty("redirectUrl").GetString());
    }

    [Theory]
    [InlineData(null)]              // setting absent entirely
    [InlineData("")]                // set but empty
    [InlineData("/insights")]       // a bare path — no origin to return to
    [InlineData("https:///insights")] // DOMAIN was empty when compose expanded the value
    public async Task AnUnusableConfiguration_SendsNoRedirectAtAll(string? configured)
    {
        // Better to omit the field than to hand the provider something it cannot return to.
        // The accompanying LogError is the operator's signal that the journey is one-way.
        var body = await SendJourneyAsync(configured);

        Assert.False(body.TryGetProperty("redirectUrl", out _));
    }
}
