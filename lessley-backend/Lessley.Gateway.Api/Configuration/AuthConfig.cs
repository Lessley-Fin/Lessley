namespace Lessley.Gateway.Api.Configuration
{
    public class AuthConfig
    {
        // Rotate the refresh token on every use so a leaked token is single-use.
        public bool IsRotateRefresh { get; set; } = true;

        public int RefreshTimeoutHours { get; set; } = 12;

        // Short-lived access token; rotation keeps sessions alive without a long-lived JWT.
        public int AccessTimeoutMinutes { get; set; } = 30;

        // Auth cookie settings. CookieDomain lets the httpOnly session cookies (and the
        // readable XSRF cookie) be shared across sub-domains (e.g. ".lessley.example.com"
        // so app.* and api.* see them). Leave null for host-only cookies (local dev).
        public string? CookieDomain { get; set; } = null;

        // "Strict" (default, safest) works when the SPA and API share a registrable domain.
        // Use "None" only for a genuinely cross-site frontend (requires HTTPS/Secure).
        public string CookieSameSite { get; set; } = "Strict";

        public AuthConfig() { }
    }
}
