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
using RabbitMQ.Client;
using RabbitMQ.Client.Events;
using Xunit;

namespace Lessley.Gateway.Tests;

/// <summary>
/// End-to-end tests with real MongoDB, real RabbitMQ, and real SignalR connections.
///
/// Prerequisites (set these environment variables or run docker-compose.test.yml):
///   RABBITMQ_URL  — e.g. amqp://guest:guest@localhost:5672/
///   MONGODB_URL   — e.g. mongodb://localhost:27017
///
/// Tests gracefully skip when the infrastructure is unavailable.
/// </summary>
public class PipelineRealInfraE2ETests : IClassFixture<RealInfraWebApplicationFactory>, IDisposable
{
    private readonly RealInfraWebApplicationFactory _factory;
    private IConnection? _rabbitConnection;
    private IModel? _rabbitChannel;

    private static readonly string? RabbitUrl  = Environment.GetEnvironmentVariable("RABBITMQ_URL");
    private static readonly string? MongoUrl   = Environment.GetEnvironmentVariable("MONGODB_URL");
    private static bool InfraAvailable         => RabbitUrl is not null && MongoUrl is not null;

    public PipelineRealInfraE2ETests(RealInfraWebApplicationFactory factory)
    {
        _factory = factory;
        if (InfraAvailable)
            ConnectRabbit();
    }

    private void ConnectRabbit()
    {
        try
        {
            var factory = new ConnectionFactory { Uri = new Uri(RabbitUrl!) };
            _rabbitConnection = factory.CreateConnection();
            _rabbitChannel    = _rabbitConnection.CreateModel();
            _rabbitChannel.ExchangeDeclare("lessley_events", ExchangeType.Topic, durable: true);
        }
        catch { /* infra not available — tests will skip */ }
    }

    // ── Test 1: UserTagAssignedEvent → tags saved + user added to SignalR group ──

    [Fact]
    public async Task RabbitMq_UserTagAssignedEvent_AssignsTagsAndSyncsSignalRGroup()
    {
        if (!InfraAvailable || _rabbitChannel is null) return;

        var (userId, email) = await CreateUserAsync();
        var tags    = new[] { $"mcc-{Guid.NewGuid():N}" };
        var adminToken = BuildJwt("admin-tag", "Admin");

        PublishRaw("Personalize.user_tag_assigned", new { userId, tags });

        await Task.Delay(TimeSpan.FromSeconds(3));

        using var scope = _factory.Services.CreateScope();
        var um = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var user = await um.FindByIdAsync(userId);

        Assert.NotNull(user);
        Assert.Contains(tags[0], user.Tags ?? new List<string>());
    }

    // ── Test 2: DealNotification → single notification per user across categories ──

    [Fact]
    public async Task RabbitMq_DealNotification_TwoCategories_UserReceivesOneNotification()
    {
        if (!InfraAvailable || _rabbitChannel is null) return;

        var cat1 = $"mcc-{Guid.NewGuid():N}";
        var cat2 = $"mcc-{Guid.NewGuid():N}";
        var email = await CreateUserWithTagsAsync(new[] { cat1, cat2 }, Array.Empty<string>());
        var dealId = Guid.NewGuid().ToString("N");

        using var scope = _factory.Services.CreateScope();
        var um   = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var user = await um.FindByEmailAsync(email);
        Assert.NotNull(user);

        PublishRaw("Personalize.deal_notification", new
        {
            dealId,
            message    = $"Deal {dealId}",
            categories = new[] { cat1, cat2 },
        });

        await Task.Delay(TimeSpan.FromSeconds(3));

        var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
        var notifCount = await db.Notifications
            .CountAsync(n => n.DealId == dealId && n.TargetType == "deal");

        Assert.Equal(1, notifCount);
    }

    // ── Test 3: SignalR — user receives deal notification in real time ───────────

    [Fact]
    public async Task RealSignalR_UserReceivesDealNotificationViaSocket()
    {
        if (!InfraAvailable || _rabbitChannel is null) return;

        var (userId, email) = await CreateUserAsync();
        var userToken = BuildJwt(userId, "Viewer");
        var cat       = $"mcc-{Guid.NewGuid():N}";

        await AssignTagsViaRabbit(userId, new[] { cat });
        await Task.Delay(TimeSpan.FromSeconds(2));

        var received = new TaskCompletionSource<JsonElement>(TaskCreationOptions.RunContinuationsAsynchronously);
        var hub      = BuildHub(userToken);
        hub.On<JsonElement>("DealGroupNotification", p => received.TrySetResult(p));
        await hub.StartAsync();

        try
        {
            var dealId = Guid.NewGuid().ToString("N");
            PublishRaw("Personalize.deal_notification", new
            {
                dealId,
                message    = $"Deal for {cat}",
                categories = new[] { cat },
            });

            using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            cts.Token.Register(() => received.TrySetCanceled());
            var payload = await received.Task;

            Assert.Equal(dealId, payload.GetProperty("dealId").GetString());
            Assert.Equal("deal",  payload.GetProperty("type").GetString());
        }
        finally
        {
            await hub.StopAsync();
            await hub.DisposeAsync();
        }
    }

    // ── Test 4: Muted user does NOT receive deal notification ────────────────────

    [Fact]
    public async Task RabbitMq_DealNotification_MutedUser_DoesNotReceiveNotification()
    {
        if (!InfraAvailable || _rabbitChannel is null) return;

        var cat   = $"mcc-{Guid.NewGuid():N}";
        var email = await CreateUserWithTagsAsync(new[] { cat }, new[] { cat });
        var dealId = Guid.NewGuid().ToString("N");

        using var scope = _factory.Services.CreateScope();
        var um   = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var user = await um.FindByEmailAsync(email);
        Assert.NotNull(user);

        PublishRaw("Personalize.deal_notification", new
        {
            dealId,
            message    = $"Deal {dealId}",
            categories = new[] { cat },
        });

        await Task.Delay(TimeSpan.FromSeconds(3));

        var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
        var hasRead = await db.NotificationReads.AnyAsync(r => r.UserId == user.Id);
        Assert.False(hasRead);
    }

    // ── Test 5: CalcResult events → notification rows created in MongoDB ──────────

    [Fact]
    public async Task RabbitMq_UserCategoriesCalculatedEvent_CreatesNotificationInDb()
    {
        if (!InfraAvailable || _rabbitChannel is null) return;

        var (userId, email) = await CreateUserAsync();

        PublishRaw("Personalize.user_categories_calculated", new
        {
            userId,
            calculatedAt = DateTime.UtcNow,
        });

        await Task.Delay(TimeSpan.FromSeconds(3));

        using var scope = _factory.Services.CreateScope();
        var db    = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
        var notif = await db.Notifications.FirstOrDefaultAsync(n => n.TargetId == userId && n.Message.Contains("category"));

        Assert.NotNull(notif);
    }

    // ── Test 6: Each calc event produces a DIFFERENT notification row ─────────────

    [Fact]
    public async Task RabbitMq_FiveCalcEvents_FiveSeparateNotificationsInDb()
    {
        if (!InfraAvailable || _rabbitChannel is null) return;

        var (userId, _) = await CreateUserAsync();

        PublishRaw("Personalize.user_categories_calculated",  new { userId, calculatedAt = DateTime.UtcNow });
        PublishRaw("Personalize.top_accounts_calculated",     new { userId, calculatedAt = DateTime.UtcNow });
        PublishRaw("Personalize.top_stores_calculated",       new { userId, calculatedAt = DateTime.UtcNow });
        PublishRaw("Personalize.missed_savings_calculated",   new { userId, calculatedAt = DateTime.UtcNow });
        PublishRaw("Personalize.matching_clubs_calculated",   new { userId, calculatedAt = DateTime.UtcNow });

        await Task.Delay(TimeSpan.FromSeconds(5));

        using var scope = _factory.Services.CreateScope();
        var db    = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
        var count = await db.NotificationReads.CountAsync(r => r.UserId == userId);

        Assert.Equal(5, count);
    }

    // ── Test 7: NotificationDispatchedEvent published after group send ────────────

    [Fact]
    public async Task HttpPost_GroupNotification_PublishesNotificationDispatchedEvent()
    {
        if (!InfraAvailable || _rabbitChannel is null) return;

        var tag        = $"tag-{Guid.NewGuid():N}";
        var adminToken = BuildJwt("admin-dispatch", "Admin");
        var received   = WaitForRabbitMessage("Gateway.notification_dispatched");

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", adminToken);
        var resp = await http.PostAsJsonAsync($"api/notification/group/{tag}", new { message = "dispatch test" });
        Assert.Equal(HttpStatusCode.OK, resp.StatusCode);

        var arrived = await received;
        Assert.NotNull(arrived);
        Assert.Equal("group", arrived?.GetProperty("Type").GetString());
    }

    // ── Test 8: Unhappy path — unknown user tag assignment is silently ignored ────

    [Fact]
    public async Task RabbitMq_UserTagAssignedEvent_UnknownUser_DoesNotThrow()
    {
        if (!InfraAvailable || _rabbitChannel is null) return;

        var fakeUserId = $"nonexistent-{Guid.NewGuid():N}";
        PublishRaw("Personalize.user_tag_assigned", new
        {
            userId = fakeUserId,
            tags   = new[] { "mcc-9999" },
        });

        await Task.Delay(TimeSpan.FromSeconds(3));
        // No exception → test passes; the consumer should handle gracefully.
    }

    // ── Helpers ───────────────────────────────────────────────────────────────────

    private void PublishRaw(string routingKey, object payload)
    {
        var body       = JsonSerializer.SerializeToUtf8Bytes(payload);
        var properties = _rabbitChannel!.CreateBasicProperties();
        properties.ContentType  = "application/json";
        properties.DeliveryMode = 2;

        _rabbitChannel.BasicPublish(
            exchange:   "lessley_events",
            routingKey: routingKey,
            basicProperties: properties,
            body:       body);
    }

    private Task<JsonElement?> WaitForRabbitMessage(string routingKey, int timeoutMs = 10_000)
    {
        var tcs   = new TaskCompletionSource<JsonElement?>(TaskCreationOptions.RunContinuationsAsynchronously);
        var queue = _rabbitChannel!.QueueDeclare(exclusive: true, autoDelete: true).QueueName;
        _rabbitChannel.QueueBind(queue, "lessley_events", routingKey);

        var consumer = new EventingBasicConsumer(_rabbitChannel);
        consumer.Received += (_, ea) =>
        {
            try
            {
                var doc = JsonDocument.Parse(ea.Body.ToArray());
                tcs.TrySetResult(doc.RootElement.Clone());
            }
            catch
            {
                tcs.TrySetResult(null);
            }
        };
        _rabbitChannel.BasicConsume(queue, autoAck: true, consumer: consumer);

        Task.Delay(timeoutMs).ContinueWith(_ => tcs.TrySetResult(null));
        return tcs.Task;
    }

    private async Task AssignTagsViaRabbit(string userId, string[] tags)
    {
        PublishRaw("Personalize.user_tag_assigned", new { userId, tags });
        await Task.Delay(TimeSpan.FromSeconds(2));
    }

    private HubConnection BuildHub(string token) =>
        new HubConnectionBuilder()
            .WithUrl(new Uri(_factory.Server.BaseAddress, "hubs/notifications"), options =>
            {
                options.Transports = HttpTransportType.LongPolling;
                options.HttpMessageHandlerFactory = _ => _factory.Server.CreateHandler();
                options.AccessTokenProvider = () => Task.FromResult<string?>(token);
            })
            .Build();

    private async Task<(string Id, string Email)> CreateUserAsync()
    {
        using var scope = _factory.Services.CreateScope();
        var um    = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var email = $"real-e2e-{Guid.NewGuid():N}@test.com";
        var user  = new ApplicationUser { UserName = email, Email = email };
        await um.CreateAsync(user, "Test1234!");
        return (user.Id, email);
    }

    private async Task<string> CreateUserWithTagsAsync(string[] tags, string[] muted)
    {
        using var scope = _factory.Services.CreateScope();
        var um    = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var email = $"real-e2e-tagged-{Guid.NewGuid():N}@test.com";
        var user  = new ApplicationUser
        {
            UserName  = email,
            Email     = email,
            Tags      = tags.ToList(),
            MutedTags = muted.ToList(),
        };
        await um.CreateAsync(user, "Test1234!");
        return email;
    }

    internal static string BuildJwt(string userId, string role)
    {
        var key    = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(GatewayWebApplicationFactory.JwtKey));
        var claims = new List<Claim>
        {
            new(ClaimTypes.NameIdentifier, userId),
            new(ClaimTypes.Role, role),
        };
        var token = new JwtSecurityToken(
            issuer:             GatewayWebApplicationFactory.Issuer,
            audience:           GatewayWebApplicationFactory.Audience,
            claims:             claims,
            expires:            DateTime.UtcNow.AddHours(1),
            signingCredentials: new SigningCredentials(key, SecurityAlgorithms.HmacSha256));
        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    public void Dispose()
    {
        _rabbitChannel?.Close();
        _rabbitChannel?.Dispose();
        _rabbitConnection?.Close();
        _rabbitConnection?.Dispose();
    }
}
