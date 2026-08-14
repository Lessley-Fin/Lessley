using System.Net;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

namespace Lessley.Gateway.Tests;

// End-to-end verification of the cookie/CSRF/refresh-rotation hardening. Auth flows use
// only the in-memory EF store, so these run without MongoDB.
public class AuthE2ETests : IClassFixture<GatewayWebApplicationFactory>
{
    private readonly GatewayWebApplicationFactory _factory;

    public AuthE2ETests(GatewayWebApplicationFactory factory) => _factory = factory;

    [Fact]
    public async Task Refresh_WithValidCookieAndCsrf_RotatesTokens()
    {
        using var http = _factory.CreateClient();
        var (_, csrf) = await RegisterAndLoginAsync(http);

        var refreshResp = await SendWithCsrf(http, HttpMethod.Post, "api/auth/refresh", csrf);

        Assert.Equal(HttpStatusCode.OK, refreshResp.StatusCode);
        var setCookies = SetCookies(refreshResp);
        Assert.Contains(setCookies, c => c.StartsWith("access_token="));
        Assert.Contains(setCookies, c => c.StartsWith("refresh_token="));   // rotated
    }

    [Fact]
    public async Task Logout_RevokesRefreshToken_SubsequentRefreshFails()
    {
        using var http = _factory.CreateClient();
        var (_, csrf) = await RegisterAndLoginAsync(http);

        var logoutResp = await SendWithCsrf(http, HttpMethod.Post, "api/auth/logout", csrf);
        Assert.Equal(HttpStatusCode.OK, logoutResp.StatusCode);

        var refreshResp = await SendWithCsrf(http, HttpMethod.Post, "api/auth/refresh", csrf);
        Assert.Equal(HttpStatusCode.Unauthorized, refreshResp.StatusCode);
    }

    [Fact]
    public async Task Refresh_ReusingRotatedToken_DetectsTheftAndRevokesChain()
    {
        // Manage cookies manually so we can replay an old (rotated-away) refresh token.
        using var http = _factory.CreateClient(new WebApplicationFactoryClientOptions { HandleCookies = false });

        var username = $"reuse-{Guid.NewGuid():N}";
        await RegistrationFlow.RegisterAsync(http, _factory.Emails, username, $"{username}@test.com");
        var loginResp = await http.PostAsJsonAsync("api/auth/login",
            new { UserName = username, Password = "Test1234!" });
        var refresh1 = CookieValue(loginResp, "refresh_token")!;

        // First refresh rotates refresh1 -> refresh2 (no access cookie sent, so CSRF is skipped).
        var first = await SendWithCookie(http, "api/auth/refresh", $"refresh_token={refresh1}");
        Assert.Equal(HttpStatusCode.OK, first.StatusCode);
        var refresh2 = CookieValue(first, "refresh_token")!;

        // Replaying the now-revoked refresh1 is treated as theft.
        var reuse = await SendWithCookie(http, "api/auth/refresh", $"refresh_token={refresh1}");
        Assert.Equal(HttpStatusCode.Unauthorized, reuse.StatusCode);

        // The whole chain (including refresh2) is revoked.
        var chain = await SendWithCookie(http, "api/auth/refresh", $"refresh_token={refresh2}");
        Assert.Equal(HttpStatusCode.Unauthorized, chain.StatusCode);
    }

    [Fact]
    public async Task Csrf_AuthenticatedUnsafeRequest_RequiresMatchingHeader()
    {
        using var http = _factory.CreateClient();
        var (_, csrf) = await RegisterAndLoginAsync(http);

        // Cookie present but no X-CSRF-TOKEN header -> rejected.
        var without = await http.PostAsync("api/user/recommendations/missed-savings", null);
        Assert.Equal(HttpStatusCode.Forbidden, without.StatusCode);

        // With the matching header the CSRF gate passes (controller then handles it).
        var with = await SendWithCsrf(http, HttpMethod.Post, "api/user/recommendations/missed-savings", csrf);
        Assert.NotEqual(HttpStatusCode.Forbidden, with.StatusCode);
    }

    [Fact]
    public async Task SignalR_Negotiate_IsExemptFromCsrf()
    {
        using var http = _factory.CreateClient();
        await RegisterAndLoginAsync(http);   // sets the auth cookie

        // SignalR negotiate is a cookie-bearing POST with no CSRF header; the /hubs path
        // must be exempt (otherwise the hub can never connect).
        var resp = await http.PostAsync("/hubs/notifications/negotiate?negotiateVersion=1", null);

        Assert.NotEqual(HttpStatusCode.Forbidden, resp.StatusCode);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private async Task<(string username, string csrf)> RegisterAndLoginAsync(HttpClient http)
    {
        var username = $"auth-{Guid.NewGuid():N}";
        await RegistrationFlow.RegisterAsync(http, _factory.Emails, username, $"{username}@test.com");
        var loginResp = await http.PostAsJsonAsync("api/auth/login",
            new { UserName = username, Password = "Test1234!" });
        Assert.Equal(HttpStatusCode.OK, loginResp.StatusCode);
        return (username, CookieValue(loginResp, "XSRF-TOKEN")!);
    }

    private static async Task<HttpResponseMessage> SendWithCsrf(HttpClient http, HttpMethod method, string path, string csrf)
    {
        var req = new HttpRequestMessage(method, path);
        req.Headers.Add("X-CSRF-TOKEN", csrf);
        return await http.SendAsync(req);
    }

    private static async Task<HttpResponseMessage> SendWithCookie(HttpClient http, string path, string cookie)
    {
        var req = new HttpRequestMessage(HttpMethod.Post, path);
        req.Headers.Add("Cookie", cookie);
        return await http.SendAsync(req);
    }

    private static List<string> SetCookies(HttpResponseMessage resp) =>
        resp.Headers.TryGetValues("Set-Cookie", out var v) ? v.ToList() : new List<string>();

    private static string? CookieValue(HttpResponseMessage resp, string name)
    {
        foreach (var c in SetCookies(resp))
        {
            var prefix = name + "=";
            if (c.StartsWith(prefix))
            {
                var val  = c.Substring(prefix.Length);
                var semi = val.IndexOf(';');
                return semi >= 0 ? val.Substring(0, semi) : val;
            }
        }
        return null;
    }
}
