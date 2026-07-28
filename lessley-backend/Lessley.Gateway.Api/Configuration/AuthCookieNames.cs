namespace Lessley.Gateway.Api.Configuration
{
    /// <summary>Canonical names for the auth cookies and CSRF header, shared by the
    /// AuthController (issuer), the JWT bearer cookie reader, and the CSRF middleware.</summary>
    public static class AuthCookieNames
    {
        public const string Access  = "access_token";
        public const string Refresh = "refresh_token";

        // Readable-by-JS double-submit token; echoed back in the CsrfHeader.
        public const string Csrf       = "XSRF-TOKEN";
        public const string CsrfHeader = "X-CSRF-TOKEN";

        // Refresh/logout are the only endpoints that need the refresh cookie, so scope it
        // there. Lowercase because clients match cookie Path case-sensitively — the SPA must
        // call these routes lowercase (ASP.NET routing itself is case-insensitive).
        public const string RefreshPath = "/api/auth";
    }
}
