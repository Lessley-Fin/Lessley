using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Net.Mime;
using System.Text.Json;

namespace Lessley.Gateway.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
[Produces(MediaTypeNames.Application.Json)]
public class ClubController : ControllerBase
{
    private readonly IPersonalizationProxyService _personalizationProxy;

    public ClubController(IPersonalizationProxyService personalizationProxy)
    {
        _personalizationProxy = personalizationProxy;
    }

    /// <summary>Returns the MCC category distribution for a club from Personalization.</summary>
    /// <param name="clubId">The club's unique identifier.</param>
    [HttpGet("categories")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetClubCategories([FromQuery] string clubId, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(clubId))
            return BadRequest(new { error = "clubId is required" });

        var response = await _personalizationProxy.GetClubCategoriesAsync(clubId, ct);
        var content  = await response.Content.ReadAsStringAsync(ct);
        var json     = JsonSerializer.Deserialize<JsonElement>(content);
        return StatusCode((int)response.StatusCode, json);
    }
}
