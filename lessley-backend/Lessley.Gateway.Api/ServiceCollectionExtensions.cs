using Lessley.Gateway.Api.Consumers;
using Lessley.Gateway.Api.Services.Classes;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using System.Security.Claims;
using System.Text;
using System.Threading.RateLimiting;

namespace Lessley.Gateway.Api.Extensions
{
    public static class ServiceCollectionExtensions
    {
        public static IServiceCollection AddCustomAuthentication(this IServiceCollection services, IConfiguration configuration)
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
                // SignalR WebSocket/SSE transports pass JWT via ?access_token= in the query string
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

        public static IServiceCollection AddCustomSwagger(this IServiceCollection services)
        {
            services.AddSwaggerGen(c =>
            {
                c.SwaggerDoc("v1", new OpenApiInfo { Title = "Lessley Gateway API", Version = "v1" });

                c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
                {
                    Name        = "Authorization",
                    Type        = SecuritySchemeType.Http,
                    Scheme      = "Bearer",
                    BearerFormat = "JWT",
                    In          = ParameterLocation.Header,
                    Description = "Enter JWT token with 'Bearer ' prefix"
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

        public static IServiceCollection AddNotificationServices(this IServiceCollection services)
        {
            services.AddSingleton<IConnectionManager, ConnectionManager>();
            services.AddScoped<INotificationRepository, NotificationRepository>();
            services.AddScoped<ISendNotificationService, SendNotificationService>();
            services.AddScoped<IUserTagService, UserTagService>();
            return services;
        }

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
                x.AddConsumer<SendNotificationCommandConsumer>();
                x.AddConsumer<SendUserNotificationCommandConsumer>();

                x.UsingRabbitMq((ctx, cfg) =>
                {
                    var rabbit = configuration.GetConnectionString("RabbitMq")
                        ?? "amqp://guest:guest@localhost/";
                    cfg.Host(new Uri(rabbit));

                    // Python publishes UserTagAssignedEvent with routing key "Personalize.user_tag_assigned"
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

                    // Python publishes SendGroupNotificationCommand with routing key "Personalize.send_notification"
                    cfg.ReceiveEndpoint("gateway.send_group_notification", e =>
                    {
                        e.ConfigureConsumeTopology = false;
                        e.Bind("lessley_events", b =>
                        {
                            b.ExchangeType = "topic";
                            b.Durable      = true;
                            b.RoutingKey   = "Personalize.send_notification";
                        });
                        e.UseRawJsonDeserializer();
                        e.ConfigureConsumer<SendNotificationCommandConsumer>(ctx);
                    });

                    // Python publishes SendUserNotificationCommand with routing key "Personalize.send_user_notification"
                    cfg.ReceiveEndpoint("gateway.send_user_notification", e =>
                    {
                        e.ConfigureConsumeTopology = false;
                        e.Bind("lessley_events", b =>
                        {
                            b.ExchangeType = "topic";
                            b.Durable      = true;
                            b.RoutingKey   = "Personalize.send_user_notification";
                        });
                        e.UseRawJsonDeserializer();
                        e.ConfigureConsumer<SendUserNotificationCommandConsumer>(ctx);
                    });
                });
            });

            return services;
        }
    }
}
