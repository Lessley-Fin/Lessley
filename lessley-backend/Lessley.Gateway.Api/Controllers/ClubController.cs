using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Net.Mime;

namespace Lessley.Gateway.Api.Controllers;

[ApiController]
[Route("api/clubs")]
[Produces(MediaTypeNames.Application.Json)]
public class ClubController : ControllerBase
{
    private readonly IClubRepository _clubRepository;

    public ClubController(IClubRepository clubRepository)
    {
        _clubRepository = clubRepository;
    }

    /// <summary>Returns all loyalty clubs, sourced from the clubs collection.</summary>
    [HttpGet]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetClubs(CancellationToken ct = default)
    {
        var clubs = await _clubRepository.GetClubsAsync(ct);
        return Ok(clubs);
    }
}
