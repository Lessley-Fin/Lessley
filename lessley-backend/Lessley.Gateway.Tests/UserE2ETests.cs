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

    // ── PUT /api/user/{userId} ─────────────────────────────────────────────────

    [Fact]
    public async Task UpdateUser_AsAdmin_UpdatesClubsAndMatchingScore()
    {
        var userId     = await CreateUserAsync($"user-upd-{Guid.NewGuid():N}");
        var adminToken = NotificationE2ETests.BuildJwt("admin-upd", "Admin");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var dto = new UpdateUserDto(null, null, new List<string> { "clubA", "clubB" }, 0.85);
        var response = await http.PutAsJsonAsync($"api/user/{userId}", dto);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        var clubs = body.RootElement.GetProperty("clubs").EnumerateArray().Select(c => c.GetString()).ToList();
        Assert.Contains("clubA", clubs);
        Assert.Contains("clubB", clubs);
        Assert.Equal(0.85, body.RootElement.GetProperty("matchingScore").GetDouble(), 2);
    }

    [Fact]
    public async Task UpdateUser_AsAdmin_UpdatesMutedTags()
    {
        var userId     = await CreateUserAsync($"user-muted-{Guid.NewGuid():N}");
        var adminToken = NotificationE2ETests.BuildJwt("admin-muted", "Admin");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var dto = new UpdateUserDto(null, new List<string> { "spam", "ads" }, null, null);
        var response = await http.PutAsJsonAsync($"api/user/{userId}", dto);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body      = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        var mutedTags = body.RootElement.GetProperty("mutedTags").EnumerateArray().Select(t => t.GetString()).ToList();
        Assert.Contains("spam", mutedTags);
        Assert.Contains("ads",  mutedTags);
    }

    [Fact]
    public async Task UpdateUser_AsAdmin_UpdatesTags_ReturnsUpdatedTags()
    {
        var userId     = await CreateUserAsync($"user-tags-{Guid.NewGuid():N}");
        var adminToken = NotificationE2ETests.BuildJwt("admin-tags", "Admin");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var dto = new UpdateUserDto(new List<string> { "tech", "food" }, null, null, null);
        var response = await http.PutAsJsonAsync($"api/user/{userId}", dto);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        var tags = body.RootElement.GetProperty("tags").EnumerateArray().Select(t => t.GetString()).ToList();
        Assert.Contains("tech", tags);
        Assert.Contains("food", tags);
    }

    [Fact]
    public async Task UpdateUser_NonAdminToken_Returns403()
    {
        var userId     = await CreateUserAsync($"user-unauth-{Guid.NewGuid():N}");
        var viewerToken = NotificationE2ETests.BuildJwt("viewer-user", "Viewer");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", viewerToken);

        var dto      = new UpdateUserDto(null, null, null, 0.5);
        var response = await http.PutAsJsonAsync($"api/user/{userId}", dto);

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
    }

    [Fact]
    public async Task UpdateUser_UnknownUserId_Returns404()
    {
        var adminToken = NotificationE2ETests.BuildJwt("admin-404", "Admin");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var dto      = new UpdateUserDto(null, null, null, 0.5);
        var response = await http.PutAsJsonAsync("api/user/nonexistent-user-id", dto);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task UpdateUser_WithoutToken_Returns401()
    {
        using var http = _factory.CreateClient();
        var dto        = new UpdateUserDto(null, null, null, 0.5);
        var response   = await http.PutAsJsonAsync("api/user/any-user", dto);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    // ── Auth E2E ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task Register_ValidCredentials_Returns200()
    {
        using var http = _factory.CreateClient();
        var dto        = new { UserName = $"reg-{Guid.NewGuid():N}", Email = "reg@test.com", Password = "Test1234!" };
        var response   = await http.PostAsJsonAsync("api/auth/register", dto);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task Login_ValidCredentials_ReturnsTokens()
    {
        var username = $"login-{Guid.NewGuid():N}";
        using var http = _factory.CreateClient();

        // Register first
        await http.PostAsJsonAsync("api/auth/register",
            new { UserName = username, Email = "login@test.com", Password = "Test1234!" });

        // Login
        var response = await http.PostAsJsonAsync("api/auth/login",
            new { UserName = username, Password = "Test1234!" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        Assert.True(body.RootElement.TryGetProperty("accessToken", out _));
        Assert.True(body.RootElement.TryGetProperty("refreshToken", out _));
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
    public async Task GetMe_WithValidToken_ReturnsUserInfo()
    {
        var username = $"me-{Guid.NewGuid():N}";
        using var http = _factory.CreateClient();

        await http.PostAsJsonAsync("api/auth/register",
            new { UserName = username, Email = "me@test.com", Password = "Test1234!" });

        var loginResp = await http.PostAsJsonAsync("api/auth/login",
            new { UserName = username, Password = "Test1234!" });
        var loginBody  = JsonDocument.Parse(await loginResp.Content.ReadAsStringAsync());
        var token      = loginBody.RootElement.GetProperty("accessToken").GetString()!;

        http.DefaultRequestHeaders.Authorization = new("Bearer", token);
        var meResp = await http.GetAsync("api/auth/me");

        Assert.Equal(HttpStatusCode.OK, meResp.StatusCode);
        var meBody = JsonDocument.Parse(await meResp.Content.ReadAsStringAsync());
        Assert.Equal(username, meBody.RootElement.GetProperty("userName").GetString());
        Assert.True(meBody.RootElement.TryGetProperty("email", out _));
    }

    [Fact]
    public async Task GetMe_WithoutToken_Returns401()
    {
        using var http = _factory.CreateClient();
        var response   = await http.GetAsync("api/auth/me");

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private async Task<string> CreateUserAsync(string username)
    {
        using var scope = _factory.Services.CreateScope();
        var userManager = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();

        var user   = new ApplicationUser { UserName = username, Email = $"{username}@test.com" };
        await userManager.CreateAsync(user, "Test1234!");
        return user.Id;
    }
}
