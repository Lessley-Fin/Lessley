namespace Lessley.Gateway.Api.Middleware
{
    /// <summary>
    /// Adds baseline security response headers. The gateway serves JSON (and SignalR), so a
    /// locked-down CSP is applied outside Development — in Development it is relaxed so the
    /// Swagger UI keeps working. These complement the edge headers set by the Caddy proxy.
    /// </summary>
    public class SecurityHeadersMiddleware
    {
        private readonly RequestDelegate _next;
        private readonly bool _isDevelopment;

        public SecurityHeadersMiddleware(RequestDelegate next, IWebHostEnvironment env)
        {
            _next          = next;
            _isDevelopment = env.IsDevelopment();
        }

        public Task InvokeAsync(HttpContext context)
        {
            var headers = context.Response.Headers;
            headers["X-Content-Type-Options"] = "nosniff";
            headers["X-Frame-Options"]        = "DENY";
            headers["Referrer-Policy"]        = "no-referrer";

            // API responses are JSON and never embed active content; forbid everything and
            // block framing. Skipped in Development so Swagger UI's own assets can load.
            if (!_isDevelopment)
                headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'";

            return _next(context);
        }
    }
}
