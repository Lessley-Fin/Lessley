using System.Net;
using System.Net.Http.Json;
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

        var resp = await http.PostAsJsonAsync("api/auth/register",
            new { UserName = "abc", Email = "not-an-email", Password = "Test1234!" });

        Assert.Equal(HttpStatusCode.BadRequest, resp.StatusCode);
    }

    [Fact]
    public async Task Register_ShortPassword_Returns400()
    {
        using var http = _factory.CreateClient();

        var resp = await http.PostAsJsonAsync("api/auth/register",
            new { UserName = "abc", Email = "abc@test.com", Password = "short" });

        Assert.Equal(HttpStatusCode.BadRequest, resp.StatusCode);
    }
}
