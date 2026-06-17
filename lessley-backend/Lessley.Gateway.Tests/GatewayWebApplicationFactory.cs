using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace Lessley.Gateway.Tests;

/// <summary>
/// No-op stand-in for the Personalization MassTransit publisher so tests don't require RabbitMQ.
/// </summary>
public sealed class FakePersonalizationService : IPersonalizationService
{
    public int RecalculateCallCount;

    public Task RecalculateCategoriesAsync(string userId, CancellationToken ct = default)
    {
        Interlocked.Increment(ref RecalculateCallCount);
        return Task.CompletedTask;
    }

    public Task TriggerCalculateTopAccountsAsync(string userId, CancellationToken ct = default)  => Task.CompletedTask;
    public Task TriggerCalculateTopStoresAsync(string userId, CancellationToken ct = default)    => Task.CompletedTask;
    public Task TriggerCalculateMissedSavingsAsync(string userId, CancellationToken ct = default) => Task.CompletedTask;
    public Task TriggerCalculateMatchingClubsAsync(string userId, CancellationToken ct = default) => Task.CompletedTask;
    public Task TriggerCalculateClubCategoriesAsync(string clubId, CancellationToken ct = default) => Task.CompletedTask;
}

public class GatewayWebApplicationFactory : WebApplicationFactory<Program>
{
    internal const string JwtKey = "e2e-test-secret-key-must-be-at-least-32-chars!!";
    internal const string Issuer = "test-issuer";
    internal const string Audience = "test-audience";

    public GatewayWebApplicationFactory()
    {
        Environment.SetEnvironmentVariable("JwtConfig__Key",     JwtKey);
        Environment.SetEnvironmentVariable("JwtConfig__Issuer",  Issuer);
        Environment.SetEnvironmentVariable("JwtConfig__Audience", Audience);
        Environment.SetEnvironmentVariable("ConnectionStrings__MongoDb", "mongodb://localhost:27017");
    }

    private readonly string _dbName = $"GatewayE2ETestDb_{Guid.NewGuid():N}";

    public readonly FakePersonalizationService PersonalizationService = new();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");

        builder.ConfigureTestServices(services =>
        {
            services.RemoveAll<DbContextOptions<ApplicationDbContext>>();
            services.AddDbContext<ApplicationDbContext>(options =>
                options.UseInMemoryDatabase(_dbName));

            services.RemoveAll<IPersonalizationService>();
            services.AddSingleton<IPersonalizationService>(PersonalizationService);

            // Provide a no-op IPublishEndpoint so SendNotificationService can resolve it.
            services.RemoveAll<MassTransit.IPublishEndpoint>();
            services.AddSingleton<MassTransit.IPublishEndpoint, NoOpPublishEndpoint>();
        });
    }

    protected override void Dispose(bool disposing)
    {
        Environment.SetEnvironmentVariable("JwtConfig__Key",     null);
        Environment.SetEnvironmentVariable("JwtConfig__Issuer",  null);
        Environment.SetEnvironmentVariable("JwtConfig__Audience", null);
        Environment.SetEnvironmentVariable("ConnectionStrings__MongoDb", null);
        base.Dispose(disposing);
    }
}
