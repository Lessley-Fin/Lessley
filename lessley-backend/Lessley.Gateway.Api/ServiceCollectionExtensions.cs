using Lessley.Gateway.Api.Consumers;
using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Models;
using MassTransit;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using MongoDB.EntityFrameworkCore.Extensions;
using Serilog;
using Serilog.Sinks.Grafana.Loki;
using System.Security.Claims;
using System.Text;
using System.Threading.RateLimiting;

namespace Lessley.Gateway.Api.Extensions
{
    public static class ServiceCollectionExtensions
    {
        // ── Logging ────────────────────────────────────────────────────────────

        public static WebApplicationBuilder AddSerilogLogging(this WebApplicationBuilder builder)
        {
            var lokiUrl = builder.Configuration["Loki:Url"] ?? "http://localhost:3100";

            Log.Logger = new LoggerConfiguration()
                .MinimumLevel.Information()
                .MinimumLevel.Override("Microsoft", Serilog.Events.LogEventLevel.Warning)
                .MinimumLevel.Override("Microsoft.Hosting.Lifetime", Serilog.Events.LogEventLevel.Information)
                .MinimumLevel.Override("Microsoft.AspNetCore.DataProtection", Serilog.Events.LogEventLevel.Error)
                .Enrich.FromLogContext()
                .Enrich.WithProperty("app_name", "gateway")
                .Enrich.With(new Configuration.ExceptionAsArrayEnricher())
                .WriteTo.Console(new Configuration.CustomLogFormatter())
                .WriteTo.GrafanaLoki(lokiUrl,
                    propertiesAsLabels: new[] { "app_name" },
                    textFormatter:     new Configuration.CustomLogFormatter())
                .CreateLogger();

            builder.Host.UseSerilog();
            return builder;
        }

        // ── Persistence ────────────────────────────────────────────────────────

        public static IServiceCollection AddPersistenceWithIdentity(
            this IServiceCollection services,
            IConfiguration configuration)
        {
            services.AddDbContext<ApplicationDbContext>(options =>
                options.UseMongoDB(
                    configuration.GetConnectionString("MongoDb")!,
                    "lessley"));

            services.AddIdentity<ApplicationUser, IdentityRole>()
                .AddEntityFrameworkStores<ApplicationDbContext>()
                .AddDefaultTokenProviders();

            return services;
        }

        // ── Authentication ─────────────────────────────────────────────────────

        public static IServiceCollection AddCustomAuthentication(
            this IServiceCollection services,
            IConfiguration configuration)
        {
            var jwtKey      = configuration["JwtConfig:Key"];
            var jwtIssuer   = configuration["JwtConfig:Issuer"];
            var jwtAudience = configuration["JwtConfig:Audience"];

            if (string.IsNullOrWhiteSpace(jwtKey) || string.IsNullOrWhiteSpace(jwtIssuer) || string.IsNullOrWhiteSpace(jwtAudience))
                throw new InvalidOperationException("JWT configuration is not set.");

            services.AddAuthentication(options =>
            {
                options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
                options.DefaultChallengeScheme    = JwtBearerDefaults.AuthenticationScheme;
            }).AddJwtBearer(options =>
            {
                options.TokenValidationParameters = new TokenValidationParameters
                {
                    ValidateIssuer           = true,
                    ValidateAudience         = true,
                    ValidateLifetime         = true,
                    ValidateIssuerSigningKey = true,
                    ClockSkew                = TimeSpan.Zero,
                    ValidIssuer              = jwtIssuer,
                    ValidAudience            = jwtAudience,
                    IssuerSigningKey         = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey))
                };
                // SignalR passes JWT as ?access_token= in query string
                options.Events = new JwtBearerEvents
                {
                    OnMessageReceived = context =>
                    {
                        var accessToken = context.Request.Query["access_token"];
                        if (!string.IsNullOrEmpty(accessToken) &&
                            context.Request.Path.StartsWithSegments("/hubs"))
                        {
                            context.Token = accessToken;
                        }
                        return Task.CompletedTask;
                    }
                };
            });

            return services;
        }

        // ── Rate Limiting ──────────────────────────────────────────────────────

        public static IServiceCollection AddCustomRateLimiting(this IServiceCollection services)
        {
            services.AddRateLimiter(options =>
            {
                options.RejectionStatusCode = 429;
                options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(httpContext =>
                {
                    var user = httpContext.User.Claims
                        .FirstOrDefault(d => d.Type == ClaimTypes.NameIdentifier)?.Value ?? "";

                    return RateLimitPartition.GetFixedWindowLimiter(user, _ => new FixedWindowRateLimiterOptions
                    {
                        PermitLimit       = 10,
                        Window            = TimeSpan.FromSeconds(5),
                        QueueLimit        = 2,
                        AutoReplenishment = true
                    });
                });
            });

            return services;
        }

        // ── Swagger ────────────────────────────────────────────────────────────

        public static IServiceCollection AddCustomSwagger(this IServiceCollection services)
        {
            services.AddSwaggerGen(c =>
            {
                c.SwaggerDoc("v1", new OpenApiInfo { Title = "Lessley Gateway API", Version = "v1" });

                c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
                {
                    Name         = "Authorization",
                    Type         = SecuritySchemeType.Http,
                    Scheme       = "Bearer",
                    BearerFormat = "JWT",
                    In           = ParameterLocation.Header,
                    Description  = "Enter JWT token with 'Bearer ' prefix"
                });

                c.AddSecurityRequirement(new OpenApiSecurityRequirement
                {
                    {
                        new OpenApiSecurityScheme
                        {
                            Reference = new OpenApiReference { Type = ReferenceType.SecurityScheme, Id = "Bearer" }
                        },
                        Array.Empty<string>()
                    }
                });
            });

            return services;
        }

        // ── MassTransit / RabbitMQ ─────────────────────────────────────────────

        public static IServiceCollection AddMassTransitWithRabbitMq(
            this IServiceCollection services,
            IConfiguration configuration,
            IWebHostEnvironment environment)
        {
            if (environment.IsEnvironment("Testing"))
                return services;

            services.AddMassTransit(x =>
            {
                x.AddConsumer<UserTagAssignedEventConsumer>();
                x.AddConsumer<DealTagNotificationConsumer>();
                x.AddConsumer<DealUserNotificationConsumer>();

                x.UsingRabbitMq((ctx, cfg) =>
                {
                    var rabbit = configuration.GetConnectionString("RabbitMq")
                        ?? "amqp://guest:guest@localhost/";
                    cfg.Host(new Uri(rabbit));

                    cfg.ReceiveEndpoint("gateway.user_tag_assigned", e =>
                    {
                        e.ConfigureConsumeTopology = false;
                        e.Bind("lessley_events", b =>
                        {
                            b.ExchangeType = "topic";
                            b.Durable      = true;
                            b.RoutingKey   = "Personalize.user_tag_assigned";
                        });
                        e.UseRawJsonDeserializer();
                        e.ConfigureConsumer<UserTagAssignedEventConsumer>(ctx);
                    });

                    cfg.ReceiveEndpoint("gateway.deal_group_notification", e =>
                    {
                        e.ConfigureConsumeTopology = false;
                        e.Bind("lessley_events", b =>
                        {
                            b.ExchangeType = "topic";
                            b.Durable      = true;
                            b.RoutingKey   = "Personalize.deal_group_notification";
                        });
                        e.UseRawJsonDeserializer();
                        e.ConfigureConsumer<DealTagNotificationConsumer>(ctx);
                    });

                    cfg.ReceiveEndpoint("gateway.deal_user_notification", e =>
                    {
                        e.ConfigureConsumeTopology = false;
                        e.Bind("lessley_events", b =>
                        {
                            b.ExchangeType = "topic";
                            b.Durable      = true;
                            b.RoutingKey   = "Personalize.deal_user_notification";
                        });
                        e.UseRawJsonDeserializer();
                        e.ConfigureConsumer<DealUserNotificationConsumer>(ctx);
                    });
                });
            });

            return services;
        }
    }
}
