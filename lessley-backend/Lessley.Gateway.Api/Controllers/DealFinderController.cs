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

    /// <summary>Returns a single deal with its store by deal ID.</summary>
    [HttpGet("{dealId}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetById(string dealId, CancellationToken ct = default)
    {
        var result = await _dealFinderService.GetByIdAsync(dealId, ct);

        return result switch
        {
            UserOperationResult.NotFoundResult       => NotFound(new { error = "Deal not found" }),
            UserOperationResult.Success           s  => Ok(s.Payload),
            _                                        => throw new InvalidOperationException("Unknown result"),
        };
    }

    /// <summary>Returns deals ranked by user interest, with a reserved slice of under-observed deals.</summary>
    /// <param name="limit">How many deals to return (1–50).</param>
    [HttpGet("hot")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetHot([FromQuery] int limit = 10, CancellationToken ct = default)
    {
        var result = await _dealFinderService.GetHotAsync(limit, ct);

        return result switch
        {
            UserOperationResult.Success s => Ok(s.Payload),
            _                             => throw new InvalidOperationException("Unknown result"),
        };
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
