using Lessley.Gateway.Api.Models.DealSearch;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Net.Mime;

namespace Lessley.Gateway.Api.Controllers;

[ApiController]
[Route("api/deals")]
[Authorize]
[Produces(MediaTypeNames.Application.Json)]
public class DealFinderController : ControllerBase
{
    private readonly IDealFinderService _dealFinderService;

    public DealFinderController(IDealFinderService dealFinderService)
    {
        _dealFinderService = dealFinderService;
    }

    /// <summary>Searches deals by MCC categories, store name fragment, or deal text. At least one filter is required.</summary>
    [HttpGet("search")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> Search(
        [FromQuery] string? mccs     = null,
        [FromQuery] string? store    = null,
        [FromQuery] string? deal     = null,
        [FromQuery] int     page     = 1,
        [FromQuery] int     pageSize = 20,
        CancellationToken   ct       = default)
    {
        var mccList = mccs is not null
            ? mccs.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                  .Select(s => int.TryParse(s, out var m) ? (int?)m : null)
                  .OfType<int>()
                  .ToList()
            : null;

        var query  = new DealSearchQuery(mccList, store, deal, page, pageSize);
        var result = await _dealFinderService.SearchAsync(query, ct);

        return result switch
        {
            UserOperationResult.BadRequestResult e => BadRequest(e.Payload),
            UserOperationResult.Success          s => Ok(s.Payload),
            _                                      => throw new InvalidOperationException("Unknown result"),
        };
    }
}
