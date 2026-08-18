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

public class GatewayWebApplicationFactory : WebApplicationFactory<Program>
{
    internal const string JwtKey = "e2e-test-secret-key-must-be-at-least-32-chars!!";
    internal const string Issuer = "test-issuer";
    internal const string Audience = "test-audience";
    internal const string EdgeKey = "test-edge-key";

    private readonly string _dbName = $"GatewayE2ETestDb_{Guid.NewGuid():N}";

    public readonly FakePersonalizationService PersonalizationService = new();

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
