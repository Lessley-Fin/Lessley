using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Net.Mime;

namespace Lessley.Gateway.Api.Controllers;

[ApiController]
[Route("api/mcc")]
[Authorize]
[Produces(MediaTypeNames.Application.Json)]
public class MccController : ControllerBase
{
    private readonly IMccRepository _mccRepository;

    public MccController(IMccRepository mccRepository)
    {
        _mccRepository = mccRepository;
    }

    /// <summary>Returns all MCC categories with their associated MCC codes, sourced from the mccs collection.</summary>
    [HttpGet("categories")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetCategories(CancellationToken ct = default)
    {
        var categories = await _mccRepository.GetCategoriesAsync(ct);
        return Ok(categories);
    }
}
