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

    public RealInfraWebApplicationFactory()
    {
        Environment.SetEnvironmentVariable("JwtConfig__Key",      GatewayWebApplicationFactory.JwtKey);
        Environment.SetEnvironmentVariable("JwtConfig__Issuer",   GatewayWebApplicationFactory.Issuer);
        Environment.SetEnvironmentVariable("JwtConfig__Audience",  GatewayWebApplicationFactory.Audience);
        Environment.SetEnvironmentVariable("ConnectionStrings__MongoDb",  MongoUrl);
        Environment.SetEnvironmentVariable("ConnectionStrings__RabbitMq", RabbitUrl);
    }

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        // "RealInfra" is not "Testing", so MassTransit IS wired to real RabbitMQ.
        builder.UseEnvironment("RealInfra");

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

    protected override void Dispose(bool disposing)
    {
        Environment.SetEnvironmentVariable("JwtConfig__Key",      null);
        Environment.SetEnvironmentVariable("JwtConfig__Issuer",   null);
        Environment.SetEnvironmentVariable("JwtConfig__Audience",  null);
        Environment.SetEnvironmentVariable("ConnectionStrings__MongoDb",  null);
        Environment.SetEnvironmentVariable("ConnectionStrings__RabbitMq", null);
        base.Dispose(disposing);
    }
}
