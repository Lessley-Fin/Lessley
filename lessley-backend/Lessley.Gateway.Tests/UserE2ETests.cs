using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Lessley.Gateway.Api.Models;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace Lessley.Gateway.Tests;

public class UserE2ETests : IClassFixture<GatewayWebApplicationFactory>
{
    private readonly GatewayWebApplicationFactory _factory;

    public UserE2ETests(GatewayWebApplicationFactory factory)
    {
        _factory = factory;
    }

    // ── PATCH /api/user/me ────────────────────────────────────────────────────

    [Fact]
    public async Task UpdateUser_AsAdmin_UpdatesClubsAndMatchingScore()
    {
        var email      = await CreateUserAsync();
        var adminToken = NotificationE2ETests.BuildJwt("admin-upd", "Admin", email);

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var dto      = new UpdateUserDto(null, new List<string> { "clubA", "clubB" }, "High");
        var response = await http.PatchAsJsonAsync("api/user/me", dto);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body  = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        var clubs = body.RootElement.GetProperty("clubs").EnumerateArray().Select(c => c.GetString()).ToList();
        Assert.Contains("clubA", clubs);
        Assert.Contains("clubB", clubs);
        Assert.Equal("High", body.RootElement.GetProperty("matchLevel").GetString());
    }

    [Fact]
    public async Task UpdateUser_AsAdmin_UpdatesMutedTags()
    {
        var email      = await CreateUserAsync();
        var adminToken = NotificationE2ETests.BuildJwt("admin-muted", "Admin", email);

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var dto      = new UpdateUserDto(new List<string> { "spam", "ads" }, null, null);
        var response = await http.PatchAsJsonAsync("api/user/me", dto);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body      = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        var mutedTags = body.RootElement.GetProperty("mutedTags").EnumerateArray().Select(t => t.GetString()).ToList();
        Assert.Contains("spam", mutedTags);
        Assert.Contains("ads",  mutedTags);
    }

    [Fact]
    public async Task UpdateUser_NonAdminUpdatingOwnProfile_Returns200()
    {
        var email = await CreateUserAsync();
        var viewerToken = NotificationE2ETests.BuildJwt("own-id", "Viewer", email);

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", viewerToken);

        var dto      = new UpdateUserDto(null, null, "Medium");
        var response = await http.PatchAsJsonAsync("api/user/me", dto);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        Assert.Equal("Medium", body.RootElement.GetProperty("matchLevel").GetString());
    }

    [Fact]
    public async Task UpdateUser_UnknownEmail_Returns404()
    {
        var fakeEmail  = $"nonexistent-{Guid.NewGuid():N}@test.com";
        var adminToken = NotificationE2ETests.BuildJwt("admin-404", "Admin", fakeEmail);

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var dto      = new UpdateUserDto(null, null, "Medium");
        var response = await http.PatchAsJsonAsync("api/user/me", dto);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task UpdateUser_WithoutToken_Returns401()
    {
        using var http = _factory.CreateClient();
        var dto        = new UpdateUserDto(null, null, "Medium");
        var response   = await http.PatchAsJsonAsync("api/user/me", dto);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task UpdateUser_MatchLevelChange_MarksInsightsStale()
    {
        var email      = await CreateUserAsync();
        var adminToken = NotificationE2ETests.BuildJwt("admin-recalc", "Admin", email);

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var dto      = new UpdateUserDto(null, null, "High");
        var response = await http.PatchAsJsonAsync("api/user/me", dto);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        // The Gateway no longer calls Personalization over HTTP, so nothing is recalculated
        // here. It reports that cached insights are stale and the client re-fetches them
        // through the edge.
        var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        Assert.True(body.RootElement.GetProperty("staleInsights").GetBoolean());
    }

    // ── PUT /api/admin/users/{email}/tags ─────────────────────────────────────

    [Fact]
    public async Task UpdateUserTags_AsAdmin_UpdatesTags()
    {
        var email      = await CreateUserAsync();
        var adminToken = NotificationE2ETests.BuildJwt("admin-tags", "Admin");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var response = await http.PutAsJsonAsync($"api/admin/users/{email}/tags", new[] { "tech", "food" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        var tags = body.RootElement.GetProperty("tags").EnumerateArray().Select(t => t.GetString()).ToList();
        Assert.Contains("tech", tags);
        Assert.Contains("food", tags);
    }

    [Fact]
    public async Task UpdateUserTags_AsNonAdmin_Returns403()
    {
        var email       = await CreateUserAsync();
        var viewerToken = NotificationE2ETests.BuildJwt("viewer-for-tags", "Viewer");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", viewerToken);

        var response = await http.PutAsJsonAsync($"api/admin/users/{email}/tags", new[] { "tech" });

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
    }

    [Fact]
    public async Task UpdateUserTags_UnknownUser_Returns404()
    {
        var adminToken = NotificationE2ETests.BuildJwt("admin-tags-404", "Admin");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var response = await http.PutAsJsonAsync("api/admin/users/no-such-user@test.com/tags", new[] { "tech" });

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task UpdateUserTags_WithoutToken_Returns401()
    {
        using var http = _factory.CreateClient();
        var response   = await http.PutAsJsonAsync("api/admin/users/any@test.com/tags", new[] { "tech" });

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    // ── Auth E2E ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task Register_ValidCredentials_Returns200()
    {
        using var http = _factory.CreateClient();
        var dto        = new { UserName = $"reg-{Guid.NewGuid():N}", Email = $"reg-{Guid.NewGuid():N}@test.com", Password = "Test1234!" };
        var response   = await http.PostAsJsonAsync("api/auth/register", dto);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task Register_WithPreferences_PersistsClubsMutedCategoriesAndMatchLevel()
    {
        using var http = _factory.CreateClient();

        var username = $"reg-pref-{Guid.NewGuid():N}";
        var email    = $"{username}@test.com";
        var dto = new
        {
            UserName        = username,
            Email           = email,
            Password        = "Test1234!",
            Clubs           = new[] { "clubX", "clubY" },
            MatchLevel      = "High",
            MutedCategories = new[] { "5411", "5812" },
        };

        var response = await http.PostAsJsonAsync("api/auth/register", dto);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        using var scope = _factory.Services.CreateScope();
        var userManager = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var user = await userManager.FindByEmailAsync(email);

        Assert.NotNull(user);
        Assert.Equal(0.75, user!.MatchingScore);
        Assert.Contains("clubX", user.Clubs!);
        Assert.Contains("clubY", user.Clubs!);
        Assert.Contains("5411", user.MutedTags!);
        Assert.Contains("5812", user.MutedTags!);
    }

    [Fact]
    public async Task Login_ValidCredentials_SetsAuthCookies()
    {
        var username = $"login-{Guid.NewGuid():N}";
        using var http = _factory.CreateClient();

        await http.PostAsJsonAsync("api/auth/register",
            new { UserName = username, Email = $"{username}@test.com", Password = "Test1234!" });

        var response = await http.PostAsJsonAsync("api/auth/login",
            new { UserName = username, Password = "Test1234!" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        // Tokens are delivered as httpOnly cookies, never in the body.
        var setCookies = response.Headers.TryGetValues("Set-Cookie", out var values)
            ? values.ToList() : new List<string>();
        Assert.Contains(setCookies, c => c.StartsWith("access_token="));
        Assert.Contains(setCookies, c => c.StartsWith("refresh_token="));

        var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        Assert.False(body.RootElement.TryGetProperty("accessToken", out _));
        Assert.Equal(username, body.RootElement.GetProperty("userName").GetString());
    }

    [Fact]
    public async Task Login_WrongPassword_Returns401()
    {
        using var http = _factory.CreateClient();
        var response   = await http.PostAsJsonAsync("api/auth/login",
            new { UserName = "nobody", Password = "wrong" });

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task GetMe_WithValidCookie_ReturnsUserInfo()
    {
        var username = $"me-{Guid.NewGuid():N}";
        using var http = _factory.CreateClient();

        await http.PostAsJsonAsync("api/auth/register",
            new { UserName = username, Email = $"{username}@test.com", Password = "Test1234!" });

        var loginResp = await http.PostAsJsonAsync("api/auth/login",
            new { UserName = username, Password = "Test1234!" });
        Assert.Equal(HttpStatusCode.OK, loginResp.StatusCode);

        // The auth cookies set at login flow automatically on the same client
        // (WebApplicationFactory enables cookie handling by default).
        var meResp = await http.GetAsync("api/user/me");

        Assert.Equal(HttpStatusCode.OK, meResp.StatusCode);
        var meBody = JsonDocument.Parse(await meResp.Content.ReadAsStringAsync());
        Assert.Equal(username, meBody.RootElement.GetProperty("userName").GetString());
        Assert.True(meBody.RootElement.TryGetProperty("email", out _));
    }

    [Fact]
    public async Task GetMe_WithoutToken_Returns401()
    {
        using var http = _factory.CreateClient();
        var response   = await http.GetAsync("api/user/me");

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private async Task<string> CreateUserAsync()
    {
        using var scope = _factory.Services.CreateScope();
        var userManager = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();

        var email = $"user-{Guid.NewGuid():N}@test.com";
        var user  = new ApplicationUser { UserName = email, Email = email };
        await userManager.CreateAsync(user, "Test1234!");
        return email;
    }
}
