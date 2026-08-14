using System.Net;
using System.Net.Http.Json;
using Lessley.Gateway.Api.Middleware;
using Xunit;

namespace Lessley.Gateway.Tests;

// Verifies the Phase 3 defense-in-depth: security response headers and DTO validation.
public class SecurityE2ETests : IClassFixture<GatewayWebApplicationFactory>
{
    private readonly GatewayWebApplicationFactory _factory;

    public SecurityE2ETests(GatewayWebApplicationFactory factory) => _factory = factory;

    [Fact]
    public async Task Responses_IncludeSecurityHeaders()
    {
        using var http = _factory.CreateClient();

        var resp = await http.GetAsync("api/user/me"); // 401 — headers still applied

        Assert.True(resp.Headers.TryGetValues("X-Content-Type-Options", out var nosniff));
        Assert.Equal("nosniff", Assert.Single(nosniff));
        Assert.True(resp.Headers.TryGetValues("X-Frame-Options", out var frame));
        Assert.Equal("DENY", Assert.Single(frame));
        Assert.True(resp.Headers.TryGetValues("Referrer-Policy", out _));
    }

    [Fact]
    public async Task Register_InvalidEmail_Returns400()
    {
        using var http = _factory.CreateClient();

        var resp = await http.PostAsJsonAsync("api/auth/register/start",
            new { UserName = "abc", Email = "not-an-email", Password = "Test1234!" });

        Assert.Equal(HttpStatusCode.BadRequest, resp.StatusCode);
    }

    [Fact]
    public async Task Register_ShortPassword_Returns400()
    {
        using var http = _factory.CreateClient();

        var resp = await http.PostAsJsonAsync("api/auth/register/start",
            new { UserName = "abc", Email = "abc@test.com", Password = "short" });

        Assert.Equal(HttpStatusCode.BadRequest, resp.StatusCode);
    }

    // ── Edge verification ─────────────────────────────────────────────────────
    // The Gateway must only answer requests that arrived through Caddy. This is what stops
    // a stray published port or a network-policy regression from exposing the service.

    [Fact]
    public async Task Request_WithoutEdgeKey_Returns403()
    {
        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Remove(EdgeVerificationMiddleware.EdgeKeyHeader);

        var resp = await http.GetAsync("api/user/me");

        Assert.Equal(HttpStatusCode.Forbidden, resp.StatusCode);
    }

    [Fact]
    public async Task Request_WithWrongEdgeKey_Returns403()
    {
        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Remove(EdgeVerificationMiddleware.EdgeKeyHeader);
        http.DefaultRequestHeaders.Add(EdgeVerificationMiddleware.EdgeKeyHeader, "not-the-key");

        var resp = await http.GetAsync("api/user/me");

        Assert.Equal(HttpStatusCode.Forbidden, resp.StatusCode);
    }

    [Fact]
    public async Task Health_IsReachableWithoutEdgeKey()
    {
        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Remove(EdgeVerificationMiddleware.EdgeKeyHeader);

        var resp = await http.GetAsync("health");

        Assert.NotEqual(HttpStatusCode.Forbidden, resp.StatusCode);
    }
}
