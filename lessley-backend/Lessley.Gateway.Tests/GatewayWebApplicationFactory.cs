using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Middleware;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace Lessley.Gateway.Tests;

/// <summary>
/// Stand-in for the Personalization MassTransit publisher so tests don't require RabbitMQ.
/// Category triggers are recorded, because which events cause a recalculation is behaviour
/// worth asserting rather than a detail to stub away.
/// </summary>
public sealed class FakePersonalizationService : IPersonalizationService
{
    private readonly List<string> _categoryTriggers = new();

    /// <summary>Emails a category recalculation was requested for, in order.</summary>
    public IReadOnlyList<string> CategoryTriggers
    {
        get { lock (_categoryTriggers) return _categoryTriggers.ToList(); }
    }

    public void ClearCategoryTriggers()
    {
        lock (_categoryTriggers) _categoryTriggers.Clear();
    }

    public Task TriggerCalculateUserCategoriesAsync(string userId, int days = 90, CancellationToken ct = default)
    {
        lock (_categoryTriggers) _categoryTriggers.Add(userId);
        return Task.CompletedTask;
    }

}

/// <summary>
/// Stand-in for the Open Finance provider so tests don't make outbound HTTP calls. Only the
/// connection-closing path is implemented: account deletion always revokes the bank consent, so
/// every E2E delete goes through here. The read paths throw rather than return a lie — a test
/// that starts needing them should say so loudly.
/// </summary>
public sealed class FakeOpenFinanceService : IOpenFinanceService
{
    private readonly List<string> _closedFor = new();

    /// <summary>Usernames whose connections were closed, in order.</summary>
    public IReadOnlyList<string> ClosedFor
    {
        get { lock (_closedFor) return _closedFor.ToList(); }
    }

    /// <summary>Set to make every close fail, standing in for an unreachable provider.</summary>
    public Exception? CloseFailure { get; set; }

    public Task<string> CreateAccessToken(string username) => Task.FromResult("fake-access-token");

    public Task<OBTransactionsResponse> GetTransactions(string username) =>
        throw new NotSupportedException("FakeOpenFinanceService only implements connection closing.");

    public Task<ConnectionResponse> InitiateConnectionJourney(string username, string? redirectUrl = null) =>
        throw new NotSupportedException("FakeOpenFinanceService only implements connection closing.");

    public Task<IReadOnlyList<string>> GetConnectionIdsAsync(string username, CancellationToken ct = default) =>
        Task.FromResult<IReadOnlyList<string>>(Array.Empty<string>());

    public Task CloseAllConnectionsAsync(string username, CancellationToken ct = default)
    {
        if (CloseFailure is not null)
            return Task.FromException(CloseFailure);

        lock (_closedFor) _closedFor.Add(username);
        return Task.CompletedTask;
    }
}

public class GatewayWebApplicationFactory : WebApplicationFactory<Program>
{
    internal const string JwtKey = "e2e-test-secret-key-must-be-at-least-32-chars!!";
    internal const string Issuer = "test-issuer";
    internal const string Audience = "test-audience";
    internal const string EdgeKey = "test-edge-key";

    private readonly string _dbName = $"GatewayE2ETestDb_{Guid.NewGuid():N}";

    public readonly FakePersonalizationService PersonalizationService = new();

    /// <summary>Lets tests see (and fail) the bank-consent revoke that deletion always runs.</summary>
    public readonly FakeOpenFinanceService OpenFinance = new();

    /// <summary>Lets tests read the verification codes the auth flows "emailed".</summary>
    public readonly CapturingEmailSender Emails = new();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");
        // Per-host settings, NOT process-global environment variables. xUnit runs test
        // classes in parallel, so a factory clearing globals on dispose used to yank
        // configuration out from under a host another class was still building — the
        // cause of the suite's intermittent mass 401 failures.
        builder.UseSetting("JwtConfig:Key",      JwtKey);
        builder.UseSetting("JwtConfig:Issuer",   Issuer);
        builder.UseSetting("JwtConfig:Audience", Audience);
        builder.UseSetting("ConnectionStrings:MongoDb", "mongodb://localhost:27017");
        // Exercises the real edge-verification path — ConfigureClient stamps the key
        // the way Caddy does in production.
        builder.UseSetting("Edge:ApiKey", EdgeKey);

        builder.ConfigureTestServices(services =>
        {
            services.RemoveAll<DbContextOptions<ApplicationDbContext>>();
            services.AddDbContext<ApplicationDbContext>(options =>
                options.UseInMemoryDatabase(_dbName));

            services.RemoveAll<IPersonalizationService>();
            services.AddSingleton<IPersonalizationService>(PersonalizationService);

            services.RemoveAll<IOpenFinanceService>();
            services.AddSingleton<IOpenFinanceService>(OpenFinance);

            services.RemoveAll<IEmailSender>();
            services.AddSingleton<IEmailSender>(Emails);

            // Provide a no-op IPublishEndpoint so SendNotificationService can resolve it.
            services.RemoveAll<MassTransit.IPublishEndpoint>();
            services.AddSingleton<MassTransit.IPublishEndpoint, NoOpPublishEndpoint>();
        });
    }

    /// <summary>Every test client presents the edge key, standing in for Caddy's header_up.</summary>
    protected override void ConfigureClient(HttpClient client)
    {
        client.DefaultRequestHeaders.Add(EdgeVerificationMiddleware.EdgeKeyHeader, EdgeKey);
        base.ConfigureClient(client);
    }

}
