using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace Lessley.Gateway.Api.Controllers;

/// <summary>
/// Read-only proxy endpoints to the Personalization service. The client only ever talks to the
/// Gateway; these forward the request (by email) and return the Personalization JSON unchanged.
/// </summary>
[ApiController]
[Route("api/[controller]")]
[Authorize]
public class PersonalizationController : ControllerBase
{
    private readonly IPersonalizationService _personalizationService;

    public PersonalizationController(IPersonalizationService personalizationService)
    {
        _personalizationService = personalizationService;
    }

    /// <summary>
    /// Process 7 — request club recommendations asynchronously. The Gateway acknowledges
    /// immediately (202); Personalization computes in the background and, on completion, sends a
    /// notification to the Gateway which creates a notification for the user.
    /// </summary>
    [HttpPost("club-recommendations/{email}")]
    public async Task<IActionResult> RequestClubRecommendations(string email, CancellationToken ct)
    {
        await _personalizationService.RequestClubRecommendationsAsync(email, ct);
        return Accepted(new { email, message = "Club recommendation request accepted" });
    }

    /// <summary>Process 4 — preferred accounts calculation (read-only).</summary>
    [HttpGet("accounts/{email}")]
    public async Task<IActionResult> GetPreferredAccounts(string email, CancellationToken ct)
    {
        var json = await _personalizationService.GetPreferredAccountsAsync(email, ct);
        return Content(json, "application/json");
    }

    /// <summary>Process 5 — preferred stores calculation (read-only).</summary>
    [HttpGet("stores/{email}")]
    public async Task<IActionResult> GetPreferredStores(string email, CancellationToken ct)
    {
        var json = await _personalizationService.GetPreferredStoresAsync(email, ct);
        return Content(json, "application/json");
    }

    /// <summary>Process 6 — alternative stores calculation (read-only).</summary>
    [HttpGet("alternative-stores/{email}")]
    public async Task<IActionResult> GetAlternativeStores(string email, CancellationToken ct)
    {
        var json = await _personalizationService.GetAlternativeStoresAsync(email, ct);
        return Content(json, "application/json");
    }

    /// <summary>Process 10 — transaction breakdown by MCC (read-only).</summary>
    [HttpGet("transactions-breakdown/{email}")]
    public async Task<IActionResult> GetTransactionBreakdownByMcc(string email, CancellationToken ct)
    {
        var json = await _personalizationService.GetTransactionBreakdownByMccAsync(email, ct);
        return Content(json, "application/json");
    }
}
