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
using Microsoft.EntityFrameworkCore;
using System.Security.Claims;
using Serilog;
using Serilog.Sinks.Grafana.Loki;

var builder = WebApplication.CreateBuilder(args);

var lokiUrl = builder.Configuration["Loki:Url"] ?? "http://localhost:3100";

Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Information()
    .MinimumLevel.Override("Microsoft", Serilog.Events.LogEventLevel.Warning)
    .MinimumLevel.Override("Microsoft.Hosting.Lifetime", Serilog.Events.LogEventLevel.Information)
    .MinimumLevel.Override("Microsoft.AspNetCore.DataProtection", Serilog.Events.LogEventLevel.Error)
    .Enrich.FromLogContext()
    .Enrich.WithProperty("app_name", "gateway")
    .Enrich.With(new Lessley.Gateway.Api.Configuration.ExceptionAsArrayEnricher())
    .WriteTo.Console(new Lessley.Gateway.Api.Configuration.CustomLogFormatter())
    .WriteTo.GrafanaLoki(lokiUrl, propertiesAsLabels: new[] { "app_name" }, textFormatter: new Lessley.Gateway.Api.Configuration.CustomLogFormatter())
    .CreateLogger();

builder.Host.UseSerilog();

builder.Services.AddCors(options =>
    options.AddPolicy("DefaultCorsPolicy", policy =>
        policy.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()));

builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseMongoDB(builder.Configuration.GetConnectionString("MongoDb"), "lessley"));

builder.Services.AddIdentity<ApplicationUser, IdentityRole>()
    .AddEntityFrameworkStores<ApplicationDbContext>()
    .AddDefaultTokenProviders();

builder.Services.AddCustomAuthentication(builder.Configuration);
builder.Services.AddCustomRateLimiting();

builder.Services.Configure<AuthConfig>(builder.Configuration.GetSection(nameof(AuthConfig)));
builder.Services.Configure<JwtConfig>(builder.Configuration.GetSection(nameof(JwtConfig)));
builder.Services.AddScoped<IJwtService, JwtService>();

builder.Services.AddHttpClient<IOpenFinanceService, OpenFinanceService>(client =>
{
    var baseUrl = builder.Configuration["OpenFinanceConfig:BaseUrl"]
        ?? throw new InvalidOperationException("OpenFinance base URL must be configured");
    client.BaseAddress = new Uri(baseUrl);
});

builder.Services.AddNotificationServices();
builder.Services.AddMassTransitWithRabbitMq(builder.Configuration, builder.Environment);

builder.Services.AddControllers();
builder.Services.AddSignalR();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddCustomSwagger();

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    Log.Information("Seeding database...");
    await RoleSeeder.SeedAsync(scope.ServiceProvider);
    await UserSeeder.SeedAsync(scope.ServiceProvider);
}

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
