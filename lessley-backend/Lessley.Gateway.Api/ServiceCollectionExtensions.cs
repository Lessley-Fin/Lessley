using Lessley.Gateway.Api.Configuration;
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

            services.AddIdentity<ApplicationUser, IdentityRole>(options =>
                {
                    // Email is the cross-service user key (personalization, settings, tags) and
                    // the /me lookup does FindByEmailAsync, which throws on more than one match —
                    // so reject registering/updating a duplicate email.
                    options.User.RequireUniqueEmail = true;

                    // Lock an account after repeated failed logins to blunt brute force.
                    options.Lockout.AllowedForNewUsers      = true;
                    options.Lockout.MaxFailedAccessAttempts = 5;
                    options.Lockout.DefaultLockoutTimeSpan  = TimeSpan.FromMinutes(15);
                })
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

            // HS256 needs a high-entropy key; reject anything shorter than 256 bits.
            if (Encoding.UTF8.GetByteCount(jwtKey) < 32)
                throw new InvalidOperationException("JwtConfig:Key must be at least 32 bytes (256 bits) for HS256.");

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
                        // SignalR (WebSockets cannot set an Authorization header) may pass the
                        // token via query string on the /hubs path.
                        var accessToken = context.Request.Query["access_token"];
                        if (!string.IsNullOrEmpty(accessToken) &&
                            context.Request.Path.StartsWithSegments("/hubs"))
                        {
                            context.Token = accessToken;
                        }
                        // Otherwise the SPA sends no Authorization header — the JWT lives in an
                        // httpOnly cookie set at login. Read it from there.
                        else if (string.IsNullOrEmpty(context.Request.Headers.Authorization))
                        {
                            var cookieToken = context.Request.Cookies[AuthCookieNames.Access];
                            if (!string.IsNullOrEmpty(cookieToken))
                                context.Token = cookieToken;
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
                    // Authenticated calls partition by user id; anonymous calls partition by
                    // client IP (real IP via forwarded headers) so one caller can't share or
                    // exhaust a single global bucket.
                    var user = httpContext.User.Claims
                        .FirstOrDefault(d => d.Type == ClaimTypes.NameIdentifier)?.Value;
                    var partitionKey = !string.IsNullOrEmpty(user)
                        ? $"user:{user}"
                        : $"ip:{httpContext.Connection.RemoteIpAddress}";

                    return RateLimitPartition.GetFixedWindowLimiter(partitionKey, _ => new FixedWindowRateLimiterOptions
                    {
                        PermitLimit       = 20,
                        Window            = TimeSpan.FromSeconds(5),
                        QueueLimit        = 2,
                        AutoReplenishment = true
                    });
                });

                // Stricter limiter for the auth endpoints (login/register/refresh) to blunt
                // brute-force and credential-stuffing: 5 attempts/minute per client IP.
                options.AddPolicy("auth", httpContext =>
                    RateLimitPartition.GetFixedWindowLimiter(
                        $"auth:{httpContext.Connection.RemoteIpAddress}",
                        _ => new FixedWindowRateLimiterOptions
                        {
                            PermitLimit       = 10,
                            Window            = TimeSpan.FromMinutes(1),
                            QueueLimit        = 0,
                            AutoReplenishment = true
                        }));
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
                x.AddConsumer<DealTagNotificationConsumer>();

                // ── Consumers: Personalization calc results → Gateway ──────────
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

                    // ── Publish topology for Gateway→Personalization recommendation commands ─
                    ConfigureCommandPublish<CalculateMissedSavingsCommand>(cfg, "Gateway.calculate_missed_savings");
                    ConfigureCommandPublish<CalculateMatchingClubsCommand>(cfg, "Gateway.calculate_matching_clubs");

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
                        // The consumer throws when the write is rejected, which is almost always
                        // Identity's concurrency stamp losing to a settings save. Re-reading the
                        // user resolves it, so short spaced retries are worth more here than a
                        // trip to the error queue.
                        e.UseMessageRetry(r => r.Intervals(200, 1000, 5000));
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

                    // ── Receive: group (tag) notifications from Personalization ─
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

                    // ── Receive: recommendation result events ────────────────────
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
