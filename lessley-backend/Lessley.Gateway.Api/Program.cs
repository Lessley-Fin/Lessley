using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Extensions;
using Lessley.Gateway.Api.Hubs;
using Lessley.Gateway.Api.Middleware;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Seeders;
using Lessley.Gateway.Api.Services.Classes;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.SignalR;
using MongoDB.Driver;
using System.Security.Claims;
using Serilog;

var builder = WebApplication.CreateBuilder(args);

// ── Infrastructure ─────────────────────────────────────────────────────────────
builder.AddSerilogLogging();
builder.Services.AddPersistenceWithIdentity(builder.Configuration);
builder.Services.AddCustomAuthentication(builder.Configuration);
builder.Services.AddCustomRateLimiting();
builder.Services.AddMassTransitWithRabbitMq(builder.Configuration, builder.Environment);

// ── Forwarded headers (behind the Caddy TLS-terminating proxy) ──────────────────
// Honor X-Forwarded-Proto/-For so the app sees the original HTTPS scheme and client
// IP. The gateway is only reachable via Caddy on the private Docker network, so the
// proxy is trusted (known-proxy lists cleared).
builder.Services.Configure<Microsoft.AspNetCore.Builder.ForwardedHeadersOptions>(options =>
{
    options.ForwardedHeaders =
        Microsoft.AspNetCore.HttpOverrides.ForwardedHeaders.XForwardedFor |
        Microsoft.AspNetCore.HttpOverrides.ForwardedHeaders.XForwardedProto;
    options.KnownNetworks.Clear();
    options.KnownProxies.Clear();
});

// ── CORS ───────────────────────────────────────────────────────────────────────
var corsOrigins = builder.Configuration.GetSection("CorsOrigins").Get<string[]>()
    ?? ["http://localhost:8000"];
builder.Services.AddCors(options =>
    options.AddPolicy("DefaultCorsPolicy", policy =>
        policy.WithOrigins(corsOrigins).AllowAnyHeader().AllowAnyMethod().AllowCredentials()));

// ── Application services ───────────────────────────────────────────────────────
builder.Services.Configure<AuthConfig>(builder.Configuration.GetSection(nameof(AuthConfig)));
builder.Services.Configure<JwtConfig>(builder.Configuration.GetSection(nameof(JwtConfig)));
builder.Services.AddScoped<IJwtService, JwtService>();

builder.Services.AddHttpClient<IOpenFinanceService, OpenFinanceService>(client =>
{
    var baseUrl = builder.Configuration["OpenFinanceConfig:BaseUrl"]
        ?? throw new InvalidOperationException("OpenFinance base URL must be configured");
    client.BaseAddress = new Uri(baseUrl);
});

// No HttpClient to Personalization: the Gateway never calls it over HTTP. Client traffic
// reaches Personalization through Caddy; server-to-server work goes over RabbitMQ.
builder.Services.Configure<EdgeConfig>(builder.Configuration.GetSection("Edge"));
builder.Services.AddScoped<IPersonalizationService, PersonalizationService>();

builder.Services.AddHttpContextAccessor();
builder.Services.AddScoped<IUserService, UserService>();
builder.Services.AddSingleton<IConnectionManager, ConnectionManager>();
builder.Services.AddScoped<INotificationRepository, NotificationRepository>();
builder.Services.AddScoped<ISendNotificationService, SendNotificationService>();
builder.Services.AddScoped<INotificationService, NotificationService>();
builder.Services.AddScoped<IUserTagService, UserTagService>();

builder.Services.AddSingleton<IMongoClient>(_ =>
    new MongoClient(builder.Configuration.GetConnectionString("MongoDb")));
builder.Services.AddScoped<IDealFinderRepository, DealFinderRepository>();
builder.Services.AddScoped<IDealFinderService, DealFinderService>();
builder.Services.AddScoped<IMccRepository, MccRepository>();
builder.Services.AddScoped<IClubRepository, ClubRepository>();

// ── Framework ──────────────────────────────────────────────────────────────────
builder.Services.AddControllers()
    .AddJsonOptions(options =>
        // Accept/emit enum values (e.g. MatchLevel) as their string names ("High"/"Medium"/"Low").
        options.JsonSerializerOptions.Converters.Add(new System.Text.Json.Serialization.JsonStringEnumConverter()));
builder.Services.AddSignalR();
builder.Services.AddSingleton<IUserIdProvider, EmailUserIdProvider>();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddCustomSwagger();

var app = builder.Build();

// ── Database seeding ───────────────────────────────────────────────────────────
using (var scope = app.Services.CreateScope())
{
    Log.Information("Seeding database...");
    await RoleSeeder.SeedAsync(scope.ServiceProvider);
    await UserSeeder.SeedAsync(scope.ServiceProvider);
}

// ── MongoDB indexes (TTL + performance) ────────────────────────────────────────
// Skipped under the in-memory integration-test host, which has no real MongoDB.
if (!app.Environment.IsEnvironment("Testing"))
{
    var mongoConnectionString = builder.Configuration.GetConnectionString("MongoDb")!;
    await MongoIndexInitializer.CreateIndexesAsync(mongoConnectionString, "lessley");
}

// ── Middleware pipeline ────────────────────────────────────────────────────────
// Must run before anything that inspects the request scheme or client IP.
app.UseForwardedHeaders();

// Security headers on every response (defense-in-depth with the Caddy edge headers).
app.UseMiddleware<SecurityHeadersMiddleware>();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}
else
{
    // TLS is terminated at Caddy, which also redirects HTTP→HTTPS. The app only needs
    // to assert HSTS so browsers refuse future plaintext connections.
    app.UseHsts();
}

app.UseExceptionHandler(errorApp =>
{
    errorApp.Run(async context =>
    {
        var feature   = context.Features.Get<Microsoft.AspNetCore.Diagnostics.IExceptionHandlerPathFeature>();
        var exception = feature?.Error;

        Log.Error(exception, "Unhandled exception during request processing.");

        context.Response.StatusCode = 500;
        await context.Response.WriteAsJsonAsync(new { detail = "Internal server error" });
    });
});

app.UseSerilogRequestLogging(options =>
{
    options.EnrichDiagnosticContext = (diagnosticContext, httpContext) =>
    {
        var username = httpContext.User?.FindFirst(ClaimTypes.Name)?.Value
            ?? httpContext.User?.FindFirst(ClaimTypes.NameIdentifier)?.Value
            ?? "anonymous";
        diagnosticContext.Set("username", username);
        diagnosticContext.Set("request_id", httpContext.TraceIdentifier);
    };
});

app.UseRouting();
app.UseCors("DefaultCorsPolicy");
// Reject anything that did not arrive through the edge, before spending work on auth.
app.UseMiddleware<EdgeVerificationMiddleware>();
app.UseAuthentication();
app.UseMiddleware<CsrfProtectionMiddleware>();
app.UseMiddleware<LogContextMiddleware>();
// Skip rate limiting under the in-memory integration-test host, where every request
// shares a null client IP and would otherwise collide in one partition.
if (!app.Environment.IsEnvironment("Testing"))
    app.UseRateLimiter();
app.UseAuthorization();

app.MapControllers();
app.MapHub<NotificationHub>("/hubs/notifications");

app.Run();

Log.CloseAndFlush();

// Expose Program to WebApplicationFactory<Program> in the test project
public partial class Program { }
