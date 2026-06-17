using Lessley.Gateway.Api.Consumers;
using Lessley.Gateway.Api.Contracts;
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
                c.SwaggerDoc("v1", new OpenApiInfo
                {
                    Title       = "Lessley Gateway API",
                    Version     = "v1",
                    Description = "Central gateway for the Lessley loyalty optimization platform. " +
                                  "Handles authentication, user management, real-time notifications (SignalR), " +
                                  "and Open Finance integration."
                });

                c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
                {
                    Name         = "Authorization",
                    Type         = SecuritySchemeType.Http,
                    Scheme       = "Bearer",
                    BearerFormat = "JWT",
                    In           = ParameterLocation.Header,
                    Description  = "Enter your JWT access token (without the 'Bearer ' prefix — Swagger adds it automatically)."
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

                var xmlFile = $"{System.Reflection.Assembly.GetExecutingAssembly().GetName().Name}.xml";
                var xmlPath = Path.Combine(AppContext.BaseDirectory, xmlFile);
                if (File.Exists(xmlPath))
                    c.IncludeXmlComments(xmlPath);
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
                // ── Consumers: Personalization → Gateway ───────────────────────
                x.AddConsumer<UserTagAssignedEventConsumer>();
                x.AddConsumer<DealUserNotificationConsumer>();

                // ── Consumers: Personalization calc results → Gateway ──────────
                x.AddConsumer<UserCategoriesCalculatedEventConsumer>();
                x.AddConsumer<TopAccountsCalculatedEventConsumer>();
                x.AddConsumer<TopStoresCalculatedEventConsumer>();
                x.AddConsumer<MissedSavingsCalculatedEventConsumer>();
                x.AddConsumer<MatchingClubsCalculatedEventConsumer>();

                // ── Consumer: deal broadcast (consolidated, task 8) ────────────
                x.AddConsumer<DealNotificationConsumer>();

                x.UsingRabbitMq((ctx, cfg) =>
                {
                    var rabbit = configuration.GetConnectionString("RabbitMq")
                        ?? "amqp://guest:guest@localhost/";
                    cfg.Host(new Uri(rabbit));

                    // All Gateway→Personalization command publishes use raw JSON
                    // so the Python consumer can parse them without a MassTransit envelope.
                    cfg.UseRawJsonSerializer(RawSerializerOptions.AddTransportHeaders);

                    // ── Publish topology for Gateway→Personalization commands ───
                    ConfigureCommandPublish<CalculateUserCategoriesCommand>(cfg, "Gateway.calculate_user_categories");
                    ConfigureCommandPublish<CalculateTopAccountsCommand>(cfg, "Gateway.calculate_top_accounts");
                    ConfigureCommandPublish<CalculateTopStoresCommand>(cfg, "Gateway.calculate_top_stores");
                    ConfigureCommandPublish<CalculateMissedSavingsCommand>(cfg, "Gateway.calculate_missed_savings");
                    ConfigureCommandPublish<CalculateMatchingClubsCommand>(cfg, "Gateway.calculate_matching_clubs");
                    ConfigureCommandPublish<CalculateClubCategoriesCommand>(cfg, "Gateway.calculate_club_categories");

                    // NotificationDispatchedEvent — published by Gateway, consumed by E2E tests
                    ConfigureCommandPublish<NotificationDispatchedEvent>(cfg, "Gateway.notification_dispatched");

                    // ── Receive: user tag assignment ───────────────────────────
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

                    // ── Receive: direct user notifications from Personalization ─
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

                    // ── Receive: consolidated deal notification (task 8) ───────
                    cfg.ReceiveEndpoint("gateway.deal_notification", e =>
                    {
                        e.ConfigureConsumeTopology = false;
                        e.Bind("lessley_events", b =>
                        {
                            b.ExchangeType = "topic";
                            b.Durable      = true;
                            b.RoutingKey   = "Personalize.deal_notification";
                        });
                        e.UseRawJsonDeserializer();
                        e.ConfigureConsumer<DealNotificationConsumer>(ctx);
                    });

                    // ── Receive: calc result events (task 6) ───────────────────
                    cfg.ReceiveEndpoint("gateway.user_categories_calculated", e =>
                    {
                        e.ConfigureConsumeTopology = false;
                        e.Bind("lessley_events", b =>
                        {
                            b.ExchangeType = "topic";
                            b.Durable      = true;
                            b.RoutingKey   = "Personalize.user_categories_calculated";
                        });
                        e.UseRawJsonDeserializer();
                        e.ConfigureConsumer<UserCategoriesCalculatedEventConsumer>(ctx);
                    });

                    cfg.ReceiveEndpoint("gateway.top_accounts_calculated", e =>
                    {
                        e.ConfigureConsumeTopology = false;
                        e.Bind("lessley_events", b =>
                        {
                            b.ExchangeType = "topic";
                            b.Durable      = true;
                            b.RoutingKey   = "Personalize.top_accounts_calculated";
                        });
                        e.UseRawJsonDeserializer();
                        e.ConfigureConsumer<TopAccountsCalculatedEventConsumer>(ctx);
                    });

                    cfg.ReceiveEndpoint("gateway.top_stores_calculated", e =>
                    {
                        e.ConfigureConsumeTopology = false;
                        e.Bind("lessley_events", b =>
                        {
                            b.ExchangeType = "topic";
                            b.Durable      = true;
                            b.RoutingKey   = "Personalize.top_stores_calculated";
                        });
                        e.UseRawJsonDeserializer();
                        e.ConfigureConsumer<TopStoresCalculatedEventConsumer>(ctx);
                    });

                    cfg.ReceiveEndpoint("gateway.missed_savings_calculated", e =>
                    {
                        e.ConfigureConsumeTopology = false;
                        e.Bind("lessley_events", b =>
                        {
                            b.ExchangeType = "topic";
                            b.Durable      = true;
                            b.RoutingKey   = "Personalize.missed_savings_calculated";
                        });
                        e.UseRawJsonDeserializer();
                        e.ConfigureConsumer<MissedSavingsCalculatedEventConsumer>(ctx);
                    });

                    cfg.ReceiveEndpoint("gateway.matching_clubs_calculated", e =>
                    {
                        e.ConfigureConsumeTopology = false;
                        e.Bind("lessley_events", b =>
                        {
                            b.ExchangeType = "topic";
                            b.Durable      = true;
                            b.RoutingKey   = "Personalize.matching_clubs_calculated";
                        });
                        e.UseRawJsonDeserializer();
                        e.ConfigureConsumer<MatchingClubsCalculatedEventConsumer>(ctx);
                    });
                });
            });

            return services;
        }

        private static void ConfigureCommandPublish<T>(IRabbitMqBusFactoryConfigurator cfg, string routingKey)
            where T : class
        {
            cfg.Message<T>(m => m.SetEntityName("lessley_events"));
            cfg.Publish<T>(p =>
            {
                p.ExchangeType = "topic";
                p.Durable      = true;
            });
            cfg.Send<T>(s => s.UseRoutingKeyFormatter(_ => routingKey));
        }
    }
}
