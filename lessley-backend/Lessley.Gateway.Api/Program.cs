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
using System.Security.Claims;
using Serilog;

var builder = WebApplication.CreateBuilder(args);

// ── Infrastructure ─────────────────────────────────────────────────────────────
builder.AddSerilogLogging();
builder.Services.AddPersistenceWithIdentity(builder.Configuration);
builder.Services.AddCustomAuthentication(builder.Configuration);
builder.Services.AddCustomRateLimiting();
builder.Services.AddMassTransitWithRabbitMq(builder.Configuration, builder.Environment);

// ── CORS ───────────────────────────────────────────────────────────────────────
builder.Services.AddCors(options =>
    options.AddPolicy("DefaultCorsPolicy", policy =>
        policy.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()));

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

builder.Services.AddScoped<IPersonalizationService, PersonalizationService>();

builder.Services.AddHttpContextAccessor();
builder.Services.AddScoped<IUserService, UserService>();
builder.Services.AddSingleton<IConnectionManager, ConnectionManager>();
builder.Services.AddScoped<INotificationRepository, NotificationRepository>();
builder.Services.AddScoped<INotificationReadRepository, NotificationReadRepository>();
builder.Services.AddScoped<ISendNotificationService, SendNotificationService>();
builder.Services.AddScoped<INotificationService, NotificationService>();
builder.Services.AddScoped<IUserTagService, UserTagService>();

// ── Framework ──────────────────────────────────────────────────────────────────
builder.Services.AddControllers()
    .AddJsonOptions(options =>
        // Accept/emit enum values (e.g. MatchLevel) as their string names ("High"/"Medium"/"Low").
        options.JsonSerializerOptions.Converters.Add(new System.Text.Json.Serialization.JsonStringEnumConverter()));
builder.Services.AddSignalR();
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
var mongoConnectionString = builder.Configuration.GetConnectionString("MongoDb")!;
await MongoIndexInitializer.CreateIndexesAsync(mongoConnectionString, "lessley");

// ── Middleware pipeline ────────────────────────────────────────────────────────
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
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

app.UseCors("DefaultCorsPolicy");
app.UseAuthentication();
app.UseMiddleware<LogContextMiddleware>();
app.UseRateLimiter();
app.UseAuthorization();

app.MapControllers();
app.MapHub<NotificationHub>("/hubs/notifications");

app.Run();

Log.CloseAndFlush();

// Expose Program to WebApplicationFactory<Program> in the test project
public partial class Program { }
