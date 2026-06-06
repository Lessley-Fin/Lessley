using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text;
using System.Text.Json;
using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Models;
using Microsoft.AspNetCore.Http.Connections;
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
        const string userId = "e2e-user-001";
        var message = $"E2E notification – {Guid.NewGuid()}";

        var userToken  = BuildJwt(userId, "Viewer");
        var adminToken = BuildJwt("admin-e2e", "Admin");

        var received = new TaskCompletionSource<JsonElement>(
            TaskCreationOptions.RunContinuationsAsynchronously);

        var hub = BuildHubConnection(userToken);
        hub.On<JsonElement>("ReceiveNotification", payload => received.TrySetResult(payload));

        await hub.StartAsync();
        try
        {
            using var http = _factory.CreateClient();
            http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

            var response = await http.PostAsJsonAsync(
                $"api/notification/user/{userId}",
                new SendNotificationDto(message));

            Assert.Equal(HttpStatusCode.OK, response.StatusCode);

            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            timeout.Token.Register(() => received.TrySetCanceled());
            var payload = await received.Task;

            Assert.Equal(message,        payload.GetProperty("message").GetString());
            Assert.Equal("notification", payload.GetProperty("type").GetString());

            // Notification should be persisted
            using var scope = _factory.Services.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
            var saved = await db.Notifications
                .FirstOrDefaultAsync(n => n.TargetId == userId && n.Message == message);

            Assert.NotNull(saved);
            Assert.Equal("user", saved.TargetType);
            Assert.False(saved.IsRead);
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
        Assert.False(saved.IsRead);
    }

    // ── Connection Status ──────────────────────────────────────────────────────

    [Fact]
    public async Task ConnectedUser_GetStatus_ReturnsConnectedTrue()
    {
        var userId    = $"status-user-{Guid.NewGuid():N}";
        var userToken = BuildJwt(userId, "Viewer");

        var hub = BuildHubConnection(userToken);
        await hub.StartAsync();
        try
        {
            using var http = _factory.CreateClient();
            http.DefaultRequestHeaders.Authorization = new("Bearer", userToken);

            var response = await http.GetAsync($"api/notification/status/{userId}");
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
        var userId    = $"offline-user-{Guid.NewGuid():N}";
        var userToken = BuildJwt(userId, "Viewer");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", userToken);

        var response = await http.GetAsync($"api/notification/status/{userId}");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        Assert.False(body.RootElement.GetProperty("isConnected").GetBoolean());
        Assert.Equal(0, body.RootElement.GetProperty("connectionCount").GetInt32());
    }

    // ── Get User Notifications ─────────────────────────────────────────────────

    [Fact]
    public async Task GetUserNotifications_AfterSendingNotification_ReturnsSavedNotification()
    {
        var userId     = $"notif-user-{Guid.NewGuid():N}";
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
            await http.PostAsJsonAsync($"api/notification/user/{userId}", new SendNotificationDto(message));

            // Retrieve user notifications
            var getResponse = await http.GetAsync($"api/notification/user/{userId}");
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
        var userId     = $"empty-user-{Guid.NewGuid():N}";
        var adminToken = BuildJwt("admin-empty", "Admin");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var response = await http.GetAsync($"api/notification/user/{userId}");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        Assert.Equal(JsonValueKind.Array, body.RootElement.ValueKind);
        Assert.Equal(0, body.RootElement.GetArrayLength());
    }

    // ── Mark Notifications as Read ─────────────────────────────────────────────

    [Fact]
    public async Task MarkAsRead_AfterSending_MarksAllNotificationsRead()
    {
        var userId     = $"read-user-{Guid.NewGuid():N}";
        var adminToken = BuildJwt("admin-mark-read", "Admin");
        var userToken  = BuildJwt(userId, "Viewer");

        var hub = BuildHubConnection(userToken);
        await hub.StartAsync();
        try
        {
            using var http = _factory.CreateClient();
            http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

            // Send two notifications
            await http.PostAsJsonAsync($"api/notification/user/{userId}", new SendNotificationDto("msg1"));
            await http.PostAsJsonAsync($"api/notification/user/{userId}", new SendNotificationDto("msg2"));

            // Mark all as read
            var markResponse = await http.PostAsync($"api/notification/read/{userId}", null);
            Assert.Equal(HttpStatusCode.OK, markResponse.StatusCode);

            // Verify they are now read in DB
            using var scope = _factory.Services.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
            var unread = await db.Notifications
                .Where(n => n.TargetId == userId && !n.IsRead)
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
        var userId     = $"no-notif-user-{Guid.NewGuid():N}";
        var adminToken = BuildJwt("admin-no-notif", "Admin");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

        var response = await http.PostAsync($"api/notification/read/{userId}", null);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
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

    private HubConnection BuildHubConnection(string token) =>
        new HubConnectionBuilder()
            .WithUrl(new Uri(_factory.Server.BaseAddress, "hubs/notifications"), options =>
            {
                options.Transports = HttpTransportType.LongPolling;
                options.HttpMessageHandlerFactory = _ => _factory.Server.CreateHandler();
                options.AccessTokenProvider = () => Task.FromResult<string?>(token);
            })
            .Build();

    internal static string BuildJwt(string userId, string role)
    {
        var key   = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(GatewayWebApplicationFactory.JwtKey));
        var token = new JwtSecurityToken(
            issuer:   GatewayWebApplicationFactory.Issuer,
            audience: GatewayWebApplicationFactory.Audience,
            claims:
            [
                new Claim(ClaimTypes.NameIdentifier, userId),
                new Claim(ClaimTypes.Role,           role),
            ],
            expires:            DateTime.UtcNow.AddHours(1),
            signingCredentials: new SigningCredentials(key, SecurityAlgorithms.HmacSha256));

        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}
