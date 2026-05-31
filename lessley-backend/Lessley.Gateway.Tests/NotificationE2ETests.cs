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

    [Fact]
    public async Task ConnectUser_AdminPostsNotification_UserReceivesMessageViaSignalR()
    {
        const string userId = "e2e-user-001";
        var message = $"E2E notification – {Guid.NewGuid()}";

        var userToken  = BuildJwt(userId, "Viewer");
        var adminToken = BuildJwt("admin-e2e", "Admin");

        // -----------------------------------------------------------------
        // 1. Open a SignalR connection as the user
        // -----------------------------------------------------------------
        var received = new TaskCompletionSource<JsonElement>(
            TaskCreationOptions.RunContinuationsAsynchronously);

        var hub = new HubConnectionBuilder()
            .WithUrl(new Uri(_factory.Server.BaseAddress, "hubs/notifications"), options =>
            {
                // LongPolling avoids WebSocket complexity with TestServer
                options.Transports = HttpTransportType.LongPolling;
                // Route all traffic through the in-process test server
                options.HttpMessageHandlerFactory = _ => _factory.Server.CreateHandler();
                // Attach the user's JWT
                options.AccessTokenProvider = () => Task.FromResult<string?>(userToken);
            })
            .Build();

        hub.On<JsonElement>("ReceiveNotification", payload =>
            received.TrySetResult(payload));

        await hub.StartAsync();
        // StartAsync() completes only after OnConnectedAsync has run on the server,
        // so the user's connection is already registered in IConnectionManager here.

        try
        {
            // -----------------------------------------------------------------
            // 2. POST a notification as admin
            // -----------------------------------------------------------------
            using var http = _factory.CreateClient();
            http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);

            var response = await http.PostAsJsonAsync(
                $"api/notification/user/{userId}",
                new SendNotificationDto(message));

            Assert.Equal(HttpStatusCode.OK, response.StatusCode);

            // -----------------------------------------------------------------
            // 3. Assert the message arrives via the SignalR connection
            // -----------------------------------------------------------------
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            timeout.Token.Register(() => received.TrySetCanceled());

            var payload = await received.Task;

            Assert.Equal(message,        payload.GetProperty("message").GetString());
            Assert.Equal("notification", payload.GetProperty("type").GetString());

            // -----------------------------------------------------------------
            // 4. Assert the notification was persisted to the DB
            // -----------------------------------------------------------------
            using var scope = _factory.Services.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

            var saved = await db.Notifications
                .FirstOrDefaultAsync(n => n.TargetId == userId && n.Message == message);

            Assert.NotNull(saved);
            Assert.Equal("user",  saved.TargetType);
            Assert.Equal(1,       saved.RecipientCount);
            Assert.True(saved.SentAt > DateTime.UtcNow.AddMinutes(-1));
        }
        finally
        {
            await hub.StopAsync();
            await hub.DisposeAsync();
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static string BuildJwt(string userId, string role)
    {
        var key   = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(GatewayWebApplicationFactory.JwtKey));
        var token = new JwtSecurityToken(
            issuer:             GatewayWebApplicationFactory.Issuer,
            audience:           GatewayWebApplicationFactory.Audience,
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
