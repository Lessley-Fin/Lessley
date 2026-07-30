namespace Lessley.Gateway.Api.Configuration;

/// <summary>
/// Trust settings for the reverse-proxy edge (Caddy). The edge is the only thing allowed to
/// reach this service: it authenticates the caller, then stamps <c>X-Edge-Key</c> on the way in
/// so the service can prove the request did not bypass it.
/// </summary>
public class EdgeConfig
{
    /// <summary>Shared secret the edge sends as <c>X-Edge-Key</c>. Server-only — never shipped
    /// to a browser. When blank, edge verification is disabled entirely.</summary>
    public string ApiKey { get; set; } = string.Empty;

    /// <summary>Development escape hatch for Mode 1 (services run locally with no Caddy in
    /// front). Only honoured when the host environment is also Development, so production
    /// cannot be opened by setting this alone.</summary>
    public bool AllowUnverifiedEdge { get; set; }
}
