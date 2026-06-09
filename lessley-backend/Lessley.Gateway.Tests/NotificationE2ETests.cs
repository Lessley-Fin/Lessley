using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text;
using System.Text.Json;
using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Models;
using Microsoft.AspNetCore.Http.Connections;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.SignalR.Client;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.IdentityModel.Tokens;
using Xunit;

namespace Lessley.Gateway.Tests;

public class NotificationE2ETests : IClassFixture<GatewayWebApplicationFactory>
{
    private readonly GatewayWebApplicationFactory _factory;

    public NotificationE2ETests(GatewayWebApplicationFactory factory)
    {
        _factory = factory;
    }

    // ── User Notification via SignalR ──────────────────────────────────────────

    [Fact]
    public async Task ConnectUser_AdminPostsNotification_UserReceivesMessageViaSignalR()
    {
        var (userId, email) = await CreateUserAsync();
        var message = $"E2E notification – {Guid.NewGuid()}";

        var userToken  = BuildJwt(userId, "Viewer");
        var adminToken = BuildJwt("admin-e2e", "Admin");

        var received = new TaskCompletionSource<JsonElement>(
            TaskCreationOptions.RunContinuationsAsynchronously);

        var hub = BuildHubConnection(userToken);
        hub.On<JsonElement>("DealUserNotification", payload => received.TrySetResult(payload));

        await hub.StartAsync();
        try
        {
            using var http = _factory.CreateClient();
            http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

            var response = await http.PostAsJsonAsync(
                $"api/notification/user/{email}",
                new SendNotificationDto(message));

            Assert.Equal(HttpStatusCode.OK, response.StatusCode);

            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            timeout.Token.Register(() => received.TrySetCanceled());
            var payload = await received.Task;

            Assert.Equal(message, payload.GetProperty("message").GetString());
            Assert.Equal("user",  payload.GetProperty("type").GetString());

            // Notification should be persisted, keyed on the resolved user.Id
            using var scope = _factory.Services.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
            var saved = await db.Notifications
                .FirstOrDefaultAsync(n => n.TargetId == userId && n.Message == message);

            Assert.NotNull(saved);
            Assert.Equal("user", saved.TargetType);
            Assert.True(saved.SentAt > DateTime.UtcNow.AddMinutes(-1));
        }
        finally
        {
            await hub.StopAsync();
            await hub.DisposeAsync();
        }
    }

    // ── Send to Group ──────────────────────────────────────────────────────────

    [Fact]
    public async Task AdminPostsGroupNotification_Returns200AndPersists()
    {
        var tag     = $"tag-{Guid.NewGuid():N}";
        var message = $"Group broadcast – {Guid.NewGuid()}";
        var adminToken = BuildJwt("admin-e2e-group", "Admin");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var response = await http.PostAsJsonAsync(
            $"api/notification/group/{tag}",
            new SendNotificationDto(message));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        using var scope = _factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
        var saved = await db.Notifications
            .FirstOrDefaultAsync(n => n.TargetId == tag && n.Message == message);

        Assert.NotNull(saved);
        Assert.Equal("group", saved.TargetType);
    }

    // ── Connection Status ──────────────────────────────────────────────────────

    [Fact]
    public async Task ConnectedUser_GetStatus_ReturnsConnectedTrue()
    {
        var (userId, email) = await CreateUserAsync();
        var userToken = BuildJwt(userId, "Viewer");

        var hub = BuildHubConnection(userToken);
        await hub.StartAsync();
        try
        {
            using var http = _factory.CreateClient();
            http.DefaultRequestHeaders.Authorization = new("Bearer", userToken);

            var response = await http.GetAsync($"api/notification/status/{email}");
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);

            var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            Assert.True(body.RootElement.GetProperty("isConnected").GetBoolean());
            Assert.True(body.RootElement.GetProperty("connectionCount").GetInt32() >= 1);
        }
        finally
        {
            await hub.StopAsync();
            await hub.DisposeAsync();
        }
    }

    [Fact]
    public async Task DisconnectedUser_GetStatus_ReturnsConnectedFalse()
    {
        var (_, email) = await CreateUserAsync();

        // Use any valid token; status is read-only and resolves the target by email.
        var token = BuildJwt("status-reader", "Viewer");
        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", token);

        var response = await http.GetAsync($"api/notification/status/{email}");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        Assert.False(body.RootElement.GetProperty("isConnected").GetBoolean());
        Assert.Equal(0, body.RootElement.GetProperty("connectionCount").GetInt32());
    }

    // ── Get User Notifications ─────────────────────────────────────────────────

    [Fact]
    public async Task GetUserNotifications_AfterSendingNotification_ReturnsSavedNotification()
    {
        var (userId, email) = await CreateUserAsync();
        var message    = $"Test message – {Guid.NewGuid()}";
        var adminToken = BuildJwt("admin-get-notif", "Admin");
        var userToken  = BuildJwt(userId, "Viewer");

        // Connect user so we can send a direct notification
        var hub = BuildHubConnection(userToken);
        await hub.StartAsync();
        try
        {
            using var http = _factory.CreateClient();
            http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

            // Send notification
            await http.PostAsJsonAsync($"api/notification/user/{email}", new SendNotificationDto(message));

            // Retrieve user notifications
            var getResponse = await http.GetAsync($"api/notification/user/{email}");
            Assert.Equal(HttpStatusCode.OK, getResponse.StatusCode);

            var notifications = JsonDocument.Parse(await getResponse.Content.ReadAsStringAsync());
            var arr           = notifications.RootElement.EnumerateArray().ToList();

            Assert.NotEmpty(arr);
            Assert.Contains(arr, n => n.GetProperty("message").GetString() == message);
            var first = arr.First(n => n.GetProperty("message").GetString() == message);
            Assert.False(first.GetProperty("isRead").GetBoolean());
        }
        finally
        {
            await hub.StopAsync();
            await hub.DisposeAsync();
        }
    }

    [Fact]
    public async Task GetUserNotifications_NoNotifications_ReturnsEmptyArray()
    {
        var (_, email) = await CreateUserAsync();
        var adminToken = BuildJwt("admin-empty", "Admin");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var response = await http.GetAsync($"api/notification/user/{email}");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        Assert.Equal(JsonValueKind.Array, body.RootElement.ValueKind);
        Assert.Equal(0, body.RootElement.GetArrayLength());
    }

    // ── Mark Notifications as Read ─────────────────────────────────────────────

    [Fact]
    public async Task MarkAsRead_AfterSending_MarksAllNotificationsRead()
    {
        var (userId, email) = await CreateUserAsync();
        var adminToken = BuildJwt("admin-mark-read", "Admin");
        var userToken  = BuildJwt(userId, "Viewer");

        var hub = BuildHubConnection(userToken);
        await hub.StartAsync();
        try
        {
            using var http = _factory.CreateClient();
            http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

            // Send two notifications
            await http.PostAsJsonAsync($"api/notification/user/{email}", new SendNotificationDto("msg1"));
            await http.PostAsJsonAsync($"api/notification/user/{email}", new SendNotificationDto("msg2"));

            // Mark all as read
            var markResponse = await http.PostAsync($"api/notification/read/{email}", null);
            Assert.Equal(HttpStatusCode.OK, markResponse.StatusCode);

            // Verify all notification_read records for this user are now marked read
            using var scope = _factory.Services.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
            var unread = await db.NotificationReads
                .Where(r => r.UserId == userId && !r.IsRead)
                .CountAsync();

            Assert.Equal(0, unread);
        }
        finally
        {
            await hub.StopAsync();
            await hub.DisposeAsync();
        }
    }

    [Fact]
    public async Task MarkAsRead_NoNotifications_Returns200()
    {
        var (_, email) = await CreateUserAsync();
        var adminToken = BuildJwt("admin-no-notif", "Admin");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var response = await http.PostAsync($"api/notification/read/{email}", null);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    // ── Muting guarantee ───────────────────────────────────────────────────────

    [Fact]
    public async Task MutedUser_DoesNotSeeGroupNotification_WhileNonMutedUserDoes()
    {
        var tag = $"deal-tag-{Guid.NewGuid():N}";
        var message = $"Deal for {tag}";

        // Subscriber has the tag and has NOT muted it; muter has the tag but muted it.
        var subscriberEmail = await CreateUserWithTagsAsync(tags: new[] { tag }, muted: Array.Empty<string>());
        var muterEmail      = await CreateUserWithTagsAsync(tags: new[] { tag }, muted: new[] { tag });

        var adminToken = BuildJwt("admin-mute-test", "Admin");
        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        // Broadcast the deal to the category tag group (Process 8 style).
        var send = await http.PostAsJsonAsync($"api/notification/group/{tag}", new SendNotificationDto(message));
        Assert.Equal(HttpStatusCode.OK, send.StatusCode);

        // The non-muted subscriber sees it in their history...
        var subNotifs = await GetNotificationsAsync(http, subscriberEmail);
        Assert.Contains(subNotifs, n => n.GetProperty("message").GetString() == message);

        // ...the muted user must never see it.
        var muterNotifs = await GetNotificationsAsync(http, muterEmail);
        Assert.DoesNotContain(muterNotifs, n => n.GetProperty("message").GetString() == message);
    }

    private async Task<List<JsonElement>> GetNotificationsAsync(HttpClient http, string email)
    {
        var resp = await http.GetAsync($"api/notification/user/{email}");
        Assert.Equal(HttpStatusCode.OK, resp.StatusCode);
        var doc = JsonDocument.Parse(await resp.Content.ReadAsStringAsync());
        return doc.RootElement.EnumerateArray().ToList();
    }

    private async Task<string> CreateUserWithTagsAsync(string[] tags, string[] muted)
    {
        using var scope = _factory.Services.CreateScope();
        var userManager = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();

        var email = $"tagged-{Guid.NewGuid():N}@test.com";
        var user  = new ApplicationUser
        {
            UserName  = email,
            Email     = email,
            Tags      = tags.ToList(),
            MutedTags = muted.ToList(),
        };
        await userManager.CreateAsync(user, "Test1234!");
        return email;
    }

    // ── Auth Required ──────────────────────────────────────────────────────────

    [Theory]
    [InlineData("GET",  "api/notification/user/any-user")]
    [InlineData("POST", "api/notification/read/any-user")]
    [InlineData("GET",  "api/notification/status/any-user")]
    public async Task Endpoints_WithoutToken_Return401(string method, string path)
    {
        using var http = _factory.CreateClient();
        var request    = new HttpRequestMessage(new HttpMethod(method), path);

        var response = await http.SendAsync(request);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private async Task<(string Id, string Email)> CreateUserAsync()
    {
        using var scope = _factory.Services.CreateScope();
        var userManager = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();

        var email = $"notif-{Guid.NewGuid():N}@test.com";
        var user  = new ApplicationUser { UserName = email, Email = email };
        await userManager.CreateAsync(user, "Test1234!");
        return (user.Id, email);
    }

    private HubConnection BuildHubConnection(string token) =>
        new HubConnectionBuilder()
            .WithUrl(new Uri(_factory.Server.BaseAddress, "hubs/notifications"), options =>
            {
                options.Transports = HttpTransportType.LongPolling;
                options.HttpMessageHandlerFactory = _ => _factory.Server.CreateHandler();
                options.AccessTokenProvider = () => Task.FromResult<string?>(token);
            })
            .Build();

    // NameIdentifier carries user.Id (SignalR identity); email is a separate claim used by
    // controllers that authorize self-service actions by email.
    internal static string BuildJwt(string userId, string role, string? email = null)
    {
        var key    = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(GatewayWebApplicationFactory.JwtKey));
        var claims = new List<Claim>
        {
            new(ClaimTypes.NameIdentifier, userId),
            new(ClaimTypes.Role,           role),
        };
        if (email is not null)
            claims.Add(new Claim(ClaimTypes.Email, email));

        var token = new JwtSecurityToken(
            issuer:   GatewayWebApplicationFactory.Issuer,
            audience: GatewayWebApplicationFactory.Audience,
            claims:             claims,
            expires:            DateTime.UtcNow.AddHours(1),
            signingCredentials: new SigningCredentials(key, SecurityAlgorithms.HmacSha256));

        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}
