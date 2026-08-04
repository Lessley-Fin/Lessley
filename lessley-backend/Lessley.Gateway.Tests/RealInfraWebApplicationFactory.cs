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
/// WebApplicationFactory that wires the Gateway against real MongoDB and real RabbitMQ.
/// Set RABBITMQ_URL and MONGODB_URL environment variables before starting the test.
/// </summary>
public class RealInfraWebApplicationFactory : WebApplicationFactory<Program>
{
    private static readonly string MongoUrl  = Environment.GetEnvironmentVariable("MONGODB_URL")  ?? "mongodb://localhost:27017";
    private static readonly string RabbitUrl = Environment.GetEnvironmentVariable("RABBITMQ_URL") ?? "amqp://guest:guest@localhost:5672/";

    private readonly string _dbName = $"GatewayE2ERealDb_{Guid.NewGuid():N}";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        // "RealInfra" is not "Testing", so MassTransit IS wired to real RabbitMQ.
        builder.UseEnvironment("RealInfra");

        // Per-host settings, NOT process-global environment variables. xUnit runs test
        // classes in parallel, so a factory clearing globals on dispose used to yank
        // configuration out from under a host another class was still building — the
        // cause of the suite's intermittent mass 401 failures.
        builder.UseSetting("JwtConfig:Key",      GatewayWebApplicationFactory.JwtKey);
        builder.UseSetting("JwtConfig:Issuer",   GatewayWebApplicationFactory.Issuer);
        builder.UseSetting("JwtConfig:Audience", GatewayWebApplicationFactory.Audience);
        builder.UseSetting("ConnectionStrings:MongoDb",  MongoUrl);
        builder.UseSetting("ConnectionStrings:RabbitMq", RabbitUrl);
        builder.UseSetting("Edge:ApiKey", GatewayWebApplicationFactory.EdgeKey);

        builder.ConfigureTestServices(services =>
        {
            // Replace EF MongoDB with a fresh test database (real MongoDB, isolated name).
            services.RemoveAll<DbContextOptions<ApplicationDbContext>>();
            services.AddDbContext<ApplicationDbContext>(options =>
                options.UseMongoDB(MongoUrl, _dbName));

            // Replace IPersonalizationService with no-op so calc trigger tests don't need
            // the Python service, but real RabbitMQ consumers still run.
            services.RemoveAll<IPersonalizationService>();
            services.AddSingleton<IPersonalizationService, FakePersonalizationService>();
        });
    }

    /// <summary>Every test client presents the edge key, standing in for Caddy's header_up.</summary>
    protected override void ConfigureClient(HttpClient client)
    {
        client.DefaultRequestHeaders.Add(
            Lessley.Gateway.Api.Middleware.EdgeVerificationMiddleware.EdgeKeyHeader,
            GatewayWebApplicationFactory.EdgeKey);
        base.ConfigureClient(client);
    }
}
