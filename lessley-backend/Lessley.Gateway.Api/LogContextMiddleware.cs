using Serilog.Context;
using System.Security.Claims;

namespace Lessley.Gateway.Api.Middleware
{
    public class LogContextMiddleware
    {
        private readonly RequestDelegate _next;

        public LogContextMiddleware(RequestDelegate next)
        {
            _next = next;
        }

        public async Task InvokeAsync(HttpContext context)
        {
            var username = context.User?.FindFirst(ClaimTypes.Name)?.Value 
                ?? context.User?.FindFirst(ClaimTypes.NameIdentifier)?.Value 
                ?? "anonymous";

            using (LogContext.PushProperty("username", username))
            using (LogContext.PushProperty("request_id", context.TraceIdentifier))
            {
                await _next(context);
            }
        }
    }
}