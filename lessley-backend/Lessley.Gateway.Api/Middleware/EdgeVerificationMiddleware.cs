using Lessley.Gateway.Api.Configuration;
using Microsoft.Extensions.Options;

namespace Lessley.Gateway.Api.Middleware
{
    /// <summary>
    /// Rejects anything that did not come through the edge (Caddy). The edge terminates TLS,
    /// authenticates the caller, and stamps <c>X-Edge-Key</c> on the inbound request; a caller
    /// that reaches this service some other way cannot produce that header.
    ///
    /// This is defense in depth, not the primary control — the primary control is that only the
    /// edge publishes ports. It exists so that a stray <c>ports:</c> entry or a network-policy
    /// regression does not silently expose the service.
    /// </summary>
    public class EdgeVerificationMiddleware
    {
        public const string EdgeKeyHeader = "X-Edge-Key";

        // Probes and dev tooling: reachable without the edge so health checks and Swagger work.
        private static readonly string[] ExemptPrefixes = { "/health", "/swagger" };

        private readonly RequestDelegate _next;
        private readonly EdgeConfig _config;
        private readonly bool _bypassActive;

        public EdgeVerificationMiddleware(
            RequestDelegate next,
            IOptions<EdgeConfig> config,
            IHostEnvironment environment,
            ILogger<EdgeVerificationMiddleware> logger)
        {
            _next   = next;
            _config = config.Value;

            // Two independent conditions, so neither a stray flag nor a mis-set environment
            // opens production on its own.
            _bypassActive = environment.IsDevelopment() && _config.AllowUnverifiedEdge;

            if (_bypassActive)
                logger.LogWarning(
                    "EDGE VERIFICATION BYPASSED — {Header} is not required. Development only; " +
                    "never set Edge:AllowUnverifiedEdge outside local debugging.", EdgeKeyHeader);
        }

        public async Task InvokeAsync(HttpContext context)
        {
            if (_bypassActive || string.IsNullOrEmpty(_config.ApiKey) || IsExempt(context.Request.Path))
            {
                await _next(context);
                return;
            }

            var presented = context.Request.Headers[EdgeKeyHeader].ToString();
            if (!string.Equals(presented, _config.ApiKey, StringComparison.Ordinal))
            {
                context.Response.StatusCode = StatusCodes.Status403Forbidden;
                await context.Response.WriteAsJsonAsync(new
                {
                    detail = "Forbidden: requests must arrive through the edge"
                });
                return;
            }

            await _next(context);
        }

        private static bool IsExempt(PathString path) =>
            ExemptPrefixes.Any(p => path.StartsWithSegments(p));
    }
}
