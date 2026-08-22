using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Net.Mime;
using System.Text.Json;

namespace Lessley.Gateway.Api.Controllers;

/// <summary>
/// Receives the browser's Content-Security-Policy violation reports (the <c>report-uri</c>
/// and <c>report-to</c> targets named by the edge policy in <c>lessley-cd/Caddyfile</c>).
/// </summary>
/// <remarks>
/// This exists so the img-src allowlist cannot fail silently. Deal imagery is scraped from
/// club and retailer CDNs, so the day a club changes CDN the only symptom is deal cards
/// quietly degrading to their emoji fallback — a report turns that into a log line on the
/// first page view instead.
///
/// Anonymous by necessity: the browser posts these on its own, outside any fetch the SPA
/// controls, and a violation on the login page has no session behind it at all.
/// </remarks>
[ApiController]
[Route("api/csp-report")]
[AllowAnonymous]
public class CspReportController : ControllerBase
{
    /// <summary>Largest report body accepted. Real reports are well under 2 KB; the cap is
    /// here so an anonymous endpoint cannot be used to push arbitrary volume into the log.</summary>
    private const int MaxReportBytes = 8 * 1024;

    private readonly ILogger<CspReportController> _logger;

    public CspReportController(ILogger<CspReportController> logger) => _logger = logger;

    /// <summary>Logs one CSP violation report. Always 204 — the browser discards the body.</summary>
    [HttpPost]
    [Consumes("application/csp-report", "application/reports+json", MediaTypeNames.Application.Json)]
    [RequestSizeLimit(MaxReportBytes)]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> Report(CancellationToken ct = default)
    {
        // Read the raw body rather than model-binding: report-uri sends a single
        // {"csp-report": {...}} under Content-Type: application/csp-report, while report-to
        // sends an array of reports as application/reports+json. One string handles both,
        // and neither shape is worth a DTO for something that only ever gets logged.
        using var reader = new StreamReader(Request.Body);
        var body = await reader.ReadToEndAsync(ct);

        if (string.IsNullOrWhiteSpace(body))
            return NoContent();

        // Log the fields worth alerting on separately from the raw body, so a new CDN host
        // can be found by querying blocked-uri instead of grepping JSON.
        var (violatedDirective, blockedUri) = ExtractSummary(body);

        _logger.LogWarning(
            "CSP violation: directive={ViolatedDirective} blocked={BlockedUri} report={Report}",
            violatedDirective ?? "unknown",
            blockedUri ?? "unknown",
            body.Length > MaxReportBytes ? body[..MaxReportBytes] : body);

        return NoContent();
    }

    /// <summary>
    /// Pulls the two interesting fields out of either report shape, tolerating anything else.
    /// A malformed body is still worth logging verbatim, so parse failure is not an error.
    /// </summary>
    private static (string? ViolatedDirective, string? BlockedUri) ExtractSummary(string body)
    {
        try
        {
            using var document = JsonDocument.Parse(body);
            var root = document.RootElement;

            // report-to delivers a batch; every report in one POST shares a policy, so the
            // first entry is representative for the summary fields.
            if (root.ValueKind == JsonValueKind.Array)
            {
                if (root.GetArrayLength() == 0) return (null, null);
                root = root[0];
                if (root.TryGetProperty("body", out var reportBody)) root = reportBody;
            }
            else if (root.TryGetProperty("csp-report", out var cspReport))
            {
                root = cspReport;
            }

            return (ReadString(root, "violatedDirective", "violated-directive"),
                    ReadString(root, "blockedURL", "blocked-uri"));
        }
        catch (JsonException)
        {
            return (null, null);
        }
    }

    /// <summary>Reads whichever spelling the browser used — the Reporting API renamed these
    /// fields to camelCase, and the older report-uri payload keeps the hyphenated names.</summary>
    private static string? ReadString(JsonElement element, params string[] names)
    {
        if (element.ValueKind != JsonValueKind.Object) return null;

        foreach (var name in names)
            if (element.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String)
                return value.GetString();

        return null;
    }
}
