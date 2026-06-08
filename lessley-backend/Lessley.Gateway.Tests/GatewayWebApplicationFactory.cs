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
/// No-op stand-in for the Personalization HTTP client so E2E tests don't require the
/// FastAPI service to be running. Records how many times recalculation was requested.
/// </summary>
public sealed class FakePersonalizationService : IPersonalizationService
{
    public int RecalculateCallCount;

    public Task RecalculateCategoriesAsync(string email, CancellationToken ct = default)
    {
        Interlocked.Increment(ref RecalculateCallCount);
        return Task.CompletedTask;
    }
}

public class GatewayWebApplicationFactory : WebApplicationFactory<Program>
{
    internal const string JwtKey = "e2e-test-secret-key-must-be-at-least-32-chars!!";
    internal const string Issuer = "test-issuer";
    internal const string Audience = "test-audience";

    public GatewayWebApplicationFactory()
    {
        // With the minimal hosting model, Program.Main configures services before
        // WebApplicationFactory's ConfigureAppConfiguration runs. Environment variables
        // are read during WebApplication.CreateBuilder(), so they arrive in time.
        // ASP.NET Core maps JwtConfig__Key → JwtConfig:Key (double-underscore separator).
        Environment.SetEnvironmentVariable("JwtConfig__Key",     JwtKey);
        Environment.SetEnvironmentVariable("JwtConfig__Issuer",  Issuer);
        Environment.SetEnvironmentVariable("JwtConfig__Audience", Audience);
        Environment.SetEnvironmentVariable("ConnectionStrings__MongoDb", "mongodb://localhost:27017");
    }

    // Each factory instance gets its own isolated in-memory database so parallel
    // test classes don't share role/user state and trigger duplicate-key errors.
    private readonly string _dbName = $"GatewayE2ETestDb_{Guid.NewGuid():N}";

    // Shared fake so tests can assert how often category recalculation was triggered.
    public readonly FakePersonalizationService PersonalizationService = new();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");

        // Replace the MongoDB-backed DbContext with EF Core InMemory so the test
        // process doesn't need a running MongoDB instance.
        builder.ConfigureTestServices(services =>
        {
            services.RemoveAll<DbContextOptions<ApplicationDbContext>>();
            services.AddDbContext<ApplicationDbContext>(options =>
                options.UseInMemoryDatabase(_dbName));

            // Replace the HTTP Personalization client with an in-memory no-op.
            services.RemoveAll<IPersonalizationService>();
            services.AddSingleton<IPersonalizationService>(PersonalizationService);
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
