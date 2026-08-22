using Lessley.Gateway.Api.Models.Interest;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Net.Mime;
using System.Security.Claims;

namespace Lessley.Gateway.Api.Controllers;

/// <summary>
/// Engagement telemetry ingest. Shares the <c>api/deals</c> prefix with
/// <see cref="DealFinderController"/> because the events are about deals — and because that
/// prefix already falls through Caddy's generic <c>/api/v1/*</c> handler to the Gateway.
/// </summary>
[ApiController]
[Route("api/deals")]
[Authorize]
[Produces(MediaTypeNames.Application.Json)]
public class InterestController : ControllerBase
{
    private readonly IInterestService _interestService;

    public InterestController(IInterestService interestService)
    {
        _interestService = interestService;
    }

    /// <summary>Records a batch of engagement events for the authenticated user.</summary>
    /// <remarks>
    /// Returns 202 rather than 200: the client fires this from a timer and never waits on the
    /// result, so the response says "taken", not "scored".
    /// </remarks>
    [HttpPost("events")]
    [ProducesResponseType(StatusCodes.Status202Accepted)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    public async Task<IActionResult> RecordEvents(
        [FromBody] InterestEventBatchDto batch,
        CancellationToken ct = default)
    {
        var result = await _interestService.RecordAsync(batch, CallerEmail(), ct);

        return result switch
        {
            UserOperationResult.BadRequestResult e => BadRequest(e.Payload),
            UserOperationResult.ForbiddenResult    => Forbid(),
            UserOperationResult.Success          s => Accepted(s.Payload),
            _                                      => throw new InvalidOperationException("Unknown result"),
        };
    }

    private string CallerEmail() => User.FindFirstValue(ClaimTypes.Email) ?? string.Empty;
}
