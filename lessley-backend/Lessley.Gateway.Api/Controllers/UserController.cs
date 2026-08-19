using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Net.Mime;
using System.Security.Claims;

namespace Lessley.Gateway.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
[Produces(MediaTypeNames.Application.Json)]
public class UserController : ControllerBase
{
    private readonly IUserService _userService;
    private readonly IOpenFinanceService _openFinanceService;

    public UserController(
        IUserService userService,
        IOpenFinanceService openFinanceService)
    {
        _userService        = userService;
        _openFinanceService = openFinanceService;
    }

    /// <summary>Returns the full configuration for the authenticated user.</summary>
    [HttpGet("me")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetMyConfig(CancellationToken ct)
    {
        var result = await _userService.GetMyConfigAsync(CallerEmail(), ct);
        return MapResult(result);
    }

    /// <summary>Initiates the Open Finance bank-connection journey for the authenticated user.</summary>
    /// <remarks>Returns the Connect URL the client should redirect the user to.</remarks>
    [HttpPost("init")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> CreateNewOpenFinanceConnection()
    {
        var connection = await _openFinanceService.InitiateConnectionJourney(CallerEmail());
        return Ok(connection);
    }

    /// <summary>Updates the authenticated user's settings: loyalty clubs, match level, or muted categories.</summary>
    [HttpPatch("me")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> UpdateUser([FromBody] UpdateUserDto dto, CancellationToken ct = default)
    {
        var result = await _userService.UpdateAsync(CallerEmail(), dto, ct);
        return MapResult(result);
    }

    /// <summary>Permanently deletes the authenticated user's account and all data owned by them.</summary>
    [HttpDelete("me")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> DeleteMyAccount(CancellationToken ct)
    {
        var result = await _userService.DeleteAsync(CallerEmail(), ct);
        return MapResult(result);
    }

    private string CallerEmail() => User.FindFirstValue(ClaimTypes.Email) ?? string.Empty;

    private IActionResult MapResult(UserOperationResult result) => result switch
    {
        UserOperationResult.NotFoundResult      => NotFound(new { error = "User not found" }),
        UserOperationResult.ForbiddenResult     => Forbid(),
        UserOperationResult.BadRequestResult  e => BadRequest(e.Payload),
        UserOperationResult.Success           s => Ok(s.Payload),
        _                                       => throw new InvalidOperationException("Unknown result"),
    };
}
