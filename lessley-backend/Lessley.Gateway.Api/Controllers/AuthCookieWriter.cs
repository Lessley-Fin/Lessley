using Lessley.Gateway.Api.Configuration;
using System.Security.Cryptography;

namespace Lessley.Gateway.Api.Controllers;

/// <summary>
/// Writes the session cookies. Pure HTTP plumbing, so it lives with the controllers rather than in
/// a service — but it is shared, because password login, OTP login and the final registration step
/// must all set byte-identical cookies for refresh and CSRF to behave the same afterwards.
/// </summary>
internal static class AuthCookieWriter
{
    public static void SetAuthCookies(
        HttpRequest request, HttpResponse response, AuthConfig config,
        string accessToken, string? rawRefreshToken)
    {
        // Request.IsHttps is true behind Caddy thanks to UseForwardedHeaders.
        var secure   = request.IsHttps;
        var sameSite = ParseSameSite(config.CookieSameSite);
        var domain   = string.IsNullOrWhiteSpace(config.CookieDomain) ? null : config.CookieDomain;

        response.Cookies.Append(AuthCookieNames.Access, accessToken, new CookieOptions
        {
            HttpOnly = true,
            Secure   = secure,
            SameSite = sameSite,
            Domain   = domain,
            Path     = "/",
            Expires  = DateTimeOffset.UtcNow.AddMinutes(config.AccessTimeoutMinutes),
        });

        if (rawRefreshToken is not null)
        {
            response.Cookies.Append(AuthCookieNames.Refresh, rawRefreshToken, new CookieOptions
            {
                HttpOnly = true,
                Secure   = secure,
                SameSite = sameSite,
                Domain   = domain,
                Path     = AuthCookieNames.RefreshPath,
                Expires  = DateTimeOffset.UtcNow.AddHours(config.RefreshTimeoutHours),
            });
        }

        // Double-submit CSRF token: readable by JS so the SPA can echo it in a header.
        // Hex (URL-safe) so the cookie value is transported verbatim — base64 would be
        // URL-encoded in Set-Cookie and then mismatch the decoded Request.Cookies value.
        var csrf = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
        response.Cookies.Append(AuthCookieNames.Csrf, csrf, new CookieOptions
        {
            HttpOnly = false,
            Secure   = secure,
            SameSite = sameSite,
            Domain   = domain,
            Path     = "/",
            Expires  = DateTimeOffset.UtcNow.AddHours(config.RefreshTimeoutHours),
        });
    }

    public static void ClearAuthCookies(HttpResponse response, AuthConfig config)
    {
        var domain = string.IsNullOrWhiteSpace(config.CookieDomain) ? null : config.CookieDomain;
        response.Cookies.Delete(AuthCookieNames.Access,  new CookieOptions { Path = "/", Domain = domain });
        response.Cookies.Delete(AuthCookieNames.Refresh, new CookieOptions { Path = AuthCookieNames.RefreshPath, Domain = domain });
        response.Cookies.Delete(AuthCookieNames.Csrf,    new CookieOptions { Path = "/", Domain = domain });
    }

    private static SameSiteMode ParseSameSite(string value) => value?.Trim().ToLowerInvariant() switch
    {
        "none" => SameSiteMode.None,
        "lax"  => SameSiteMode.Lax,
        _      => SameSiteMode.Strict,
    };
}
