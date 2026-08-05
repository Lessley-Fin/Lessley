using System.Security.Cryptography;
using System.Text;
using Lessley.Gateway.Api.Configuration;

namespace Lessley.Gateway.Api.Middleware
{
    /// <summary>
    /// Double-submit CSRF guard. Cookie-based (ambient) auth is the only thing CSRF can
    /// abuse, so on unsafe methods — and only when the request carries the access-token
    /// cookie — this requires the <c>X-CSRF-TOKEN</c> header to match the readable
    /// <c>XSRF-TOKEN</c> cookie issued at login/refresh. Bearer-header callers are unaffected.
    /// This is defense-in-depth on top of SameSite cookies.
    /// </summary>
    public class CsrfProtectionMiddleware
    {
        private readonly RequestDelegate _next;

        private static readonly HashSet<string> SafeMethods =
            new(StringComparer.OrdinalIgnoreCase) { "GET", "HEAD", "OPTIONS", "TRACE" };

        /// <summary>True for methods CSRF cannot abuse. Shared with AuthController.Verify,
        /// which applies the same rule to the forwarded method during edge authentication.</summary>
        public static bool IsSafeMethod(string method) => SafeMethods.Contains(method);

        public CsrfProtectionMiddleware(RequestDelegate next) => _next = next;

        public async Task InvokeAsync(HttpContext context)
        {
            // SignalR's negotiate is a POST that rides the auth cookie but can't carry our
            // CSRF header; hub invocations travel over the WebSocket (not CSRF-able HTTP),
            // so the /hubs path is exempt.
            if (!SafeMethods.Contains(context.Request.Method) &&
                !context.Request.Path.StartsWithSegments("/hubs") &&
                !string.IsNullOrEmpty(context.Request.Cookies[AuthCookieNames.Access]))
            {
                var headerToken = context.Request.Headers[AuthCookieNames.CsrfHeader].ToString();
                var cookieToken = context.Request.Cookies[AuthCookieNames.Csrf];

                if (string.IsNullOrEmpty(headerToken) ||
                    string.IsNullOrEmpty(cookieToken) ||
                    !CryptographicOperations.FixedTimeEquals(
                        Encoding.UTF8.GetBytes(headerToken),
                        Encoding.UTF8.GetBytes(cookieToken)))
                {
                    context.Response.StatusCode = StatusCodes.Status403Forbidden;
                    await context.Response.WriteAsJsonAsync(new { detail = "CSRF validation failed" });
                    return;
                }
            }

            await _next(context);
        }
    }
}
