using Lessley.Gateway.Api.Models.Club;
using Lessley.Gateway.Api.Models.Optimizer;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Net.Mime;
using System.Security.Claims;
using System.Text.Json;

namespace Lessley.Gateway.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
[Produces(MediaTypeNames.Application.Json)]
public class OptimizerController : ControllerBase
{
    private readonly IOptimizerProxyService _optimizerProxy;
    private readonly IUserService _userService;
    private readonly ILogger<OptimizerController> _logger;

    public OptimizerController(
        IOptimizerProxyService optimizerProxy,
        IUserService userService,
        ILogger<OptimizerController> logger)
    {
        _optimizerProxy = optimizerProxy;
        _userService    = userService;
        _logger         = logger;
    }

    /// <summary>Finds the cheapest legal stacks of deals for a cart at one store.</summary>
    /// <remarks>
    /// Eligibility comes from the caller's own saved loyalty clubs, never from the
    /// request body — a client cannot claim a membership it does not have.
    /// <para>
    /// The optimizer's response is passed through as-is: an envelope of ranked
    /// results (cheapest first) whose paths are bare deal_ids, plus a
    /// <c>deals</c> lookup so a client can render them without a round-trip per deal.
    /// </para>
    /// </remarks>
    [HttpPost("optimize")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status503ServiceUnavailable)]
    public async Task<IActionResult> Optimize([FromBody] OptimizeRequestDto request, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(request.StoreId))
            return BadRequest(new { error = "storeId is required" });

        var email = User.FindFirstValue(ClaimTypes.Email) ?? string.Empty;
        var clubs = await _userService.GetUserClubsAsync(email, ct);
        if (clubs is null)
            return NotFound(new { error = "User not found" });

        // Overwrites whatever the client sent: memberships are a server-side fact,
        // not something a caller may assert about itself. Always a list — never
        // null — so the optimizer prunes on it even when the user has joined
        // nothing; null there is reserved for "unknown user, don't prune", which
        // an authenticated /optimize call never is.
        request = request with { MemberSourceIds = ClubSourceIds.FromClubIds(clubs) };

        HttpResponseMessage response;
        try
        {
            response = await _optimizerProxy.OptimizeAsync(request, ct);
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "Deal optimizer unreachable for store {StoreId}", request.StoreId);
            return StatusCode(StatusCodes.Status503ServiceUnavailable,
                new { error = "The deal optimizer is unavailable. Please try again shortly." });
        }

        var content = await response.Content.ReadAsStringAsync(ct);
        var json    = JsonSerializer.Deserialize<JsonElement>(content);
        return StatusCode((int)response.StatusCode, json);
    }
}
