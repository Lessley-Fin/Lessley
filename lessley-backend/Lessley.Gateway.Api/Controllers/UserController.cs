using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.Extensions.Options;
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
    private readonly AuthConfig _authConfig;

    public UserController(
        IUserService userService,
        IOpenFinanceService openFinanceService,
        IOptions<AuthConfig> authConfig)
    {
        _userService        = userService;
        _openFinanceService = openFinanceService;
        _authConfig         = authConfig.Value;
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

    /// <summary>Permanently deletes the authenticated user's account.</summary>
    /// <remarks>
    /// Takes no body: the account deleted is the one in the JWT. The bank consent always goes
    /// with it — if that revoke fails, nothing is deleted and the account is left intact so the
    /// caller can retry. The confirmation the user types is checked in the client only.
    /// </remarks>
    [HttpDelete("me")]
    // Irreversible and fans out to the Open Finance provider, so it belongs on the stricter auth
    // bucket rather than the general per-user one — 10 attempts/minute per IP.
    [EnableRateLimiting("auth")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status502BadGateway)]
    public async Task<IActionResult> DeleteMyAccount(CancellationToken ct = default)
    {
        var result = await _userService.DeleteMyAccountAsync(CallerEmail(), ct);

        return result switch
        {
            AccountDeletionResult.Success => ClearCookiesAndReportDeleted(),
            AccountDeletionResult.NotFoundResult
                => NotFound(new { detail = "User not found" }),
            AccountDeletionResult.OpenFinanceFailed
                => StatusCode(StatusCodes.Status502BadGateway,
                    new { detail = "Could not close the bank connection. Nothing was deleted — please try again." }),
            _ => throw new InvalidOperationException("Unknown result"),
        };
    }

    private IActionResult ClearCookiesAndReportDeleted()
    {
        // Without this the browser keeps a session for an account that no longer exists, and
        // every subsequent call 404s until the access cookie ages out.
        AuthCookieWriter.ClearAuthCookies(Response, _authConfig);
        return NoContent();
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
