using Lessley.Gateway.Api.Models;
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
public class UserController : ControllerBase
{
    private readonly IUserService _userService;
    private readonly IOpenFinanceService _openFinanceService;
    private readonly IPersonalizationService _personalizationService;
    private readonly IPersonalizationProxyService _personalizationProxy;

    public UserController(
        IUserService userService,
        IOpenFinanceService openFinanceService,
        IPersonalizationService personalizationService,
        IPersonalizationProxyService personalizationProxy)
    {
        _userService            = userService;
        _openFinanceService     = openFinanceService;
        _personalizationService = personalizationService;
        _personalizationProxy   = personalizationProxy;
    }

    /// <summary>Returns the authenticated user's stored category tags from the database.</summary>
    [HttpGet("me/categories")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetCategories(CancellationToken ct)
    {
        var result = await _userService.GetCategoriesAsync(CallerEmail(), ct);
        return MapResult(result);
    }

    /// <summary>Returns the authenticated user's bank accounts from Personalization.</summary>
    [HttpGet("me/accounts")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetAccounts(CancellationToken ct)
    {
        var response = await _personalizationProxy.GetAccountsAsync(CallerEmail(), ct);
        return await ProxyResponse(response, ct);
    }

    /// <summary>Returns the authenticated user's financial transactions from Personalization.</summary>
    [HttpGet("me/transactions")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetTransactions(
        [FromQuery] bool? timeFilter = null,
        [FromQuery] int?  days       = null,
        CancellationToken ct = default)
    {
        var response = await _personalizationProxy.GetTransactionsAsync(CallerEmail(), timeFilter, days, ct);
        return await ProxyResponse(response, ct);
    }

    /// <summary>Returns the authenticated user's transactions for a specific bank account from Personalization.</summary>
    [HttpGet("me/transactions/by-account")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetTransactionsByAccount(
        [FromQuery] string accountId,
        [FromQuery] bool?  timeFilter = null,
        [FromQuery] int?   days       = null,
        CancellationToken  ct         = default)
    {
        if (string.IsNullOrWhiteSpace(accountId))
            return BadRequest(new { error = "accountId is required" });

        var response = await _personalizationProxy.GetTransactionsByAccountAsync(CallerEmail(), accountId, timeFilter, days, ct);
        return await ProxyResponse(response, ct);
    }

    /// <summary>Triggers a user-categories calculation via Personalization.</summary>
    [HttpPost("insights/categories")]
    [ProducesResponseType(StatusCodes.Status202Accepted)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> CalcCategories(CancellationToken ct)
    {
        var result = await _userService.RecalculateCategoriesAsync(CallerEmail(), ct);
        return result is UserOperationResult.NotFoundResult ? NotFound(new { error = "User not found" }) : Accepted();
    }

    /// <summary>Triggers a top-accounts calculation via Personalization.</summary>
    [HttpPost("insights/top-accounts")]
    [ProducesResponseType(StatusCodes.Status202Accepted)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status422UnprocessableEntity)]
    public async Task<IActionResult> CalcTopAccounts(CancellationToken ct)
    {
        var check = await CheckUserHasCategories(ct);
        if (check is not null) return check;
        await _personalizationService.TriggerCalculateTopAccountsAsync(CallerEmail(), ct);
        return Accepted();
    }

    /// <summary>Triggers a top-stores calculation via Personalization.</summary>
    [HttpPost("insights/top-stores")]
    [ProducesResponseType(StatusCodes.Status202Accepted)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status422UnprocessableEntity)]
    public async Task<IActionResult> CalcTopStores(CancellationToken ct)
    {
        var check = await CheckUserHasCategories(ct);
        if (check is not null) return check;
        await _personalizationService.TriggerCalculateTopStoresAsync(CallerEmail(), ct);
        return Accepted();
    }

    /// <summary>Triggers a missed-savings calculation via Personalization.</summary>
    [HttpPost("insights/missed-savings")]
    [ProducesResponseType(StatusCodes.Status202Accepted)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status422UnprocessableEntity)]
    public async Task<IActionResult> CalcMissedSavings(CancellationToken ct)
    {
        var check = await CheckUserHasCategories(ct);
        if (check is not null) return check;
        await _personalizationService.TriggerCalculateMissedSavingsAsync(CallerEmail(), ct);
        return Accepted();
    }

    /// <summary>Triggers a matching-clubs calculation via Personalization.</summary>
    [HttpPost("recommendations/matching-clubs")]
    [ProducesResponseType(StatusCodes.Status202Accepted)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status422UnprocessableEntity)]
    public async Task<IActionResult> CalcMatchingClubs(CancellationToken ct)
    {
        var check = await CheckUserHasCategories(ct);
        if (check is not null) return check;
        await _personalizationService.TriggerCalculateMatchingClubsAsync(CallerEmail(), ct);
        return Accepted();
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

    private string CallerEmail() => User.FindFirstValue(ClaimTypes.Email) ?? string.Empty;

    // Returns a non-null error result if the user is missing or has no categories; null means proceed.
    private async Task<IActionResult?> CheckUserHasCategories(CancellationToken ct)
    {
        var tags = await _userService.GetUserTagsAsync(CallerEmail(), ct);
        if (tags is null)
            return NotFound(new { error = "User not found" });
        if (tags.Count == 0)
            return UnprocessableEntity(new { error = "User has no categories yet. Call POST /api/user/insights/categories first." });
        return null;
    }

    private async Task<IActionResult> ProxyResponse(HttpResponseMessage response, CancellationToken ct)
    {
        var content = await response.Content.ReadAsStringAsync(ct);
        var json    = JsonSerializer.Deserialize<JsonElement>(content);
        return StatusCode((int)response.StatusCode, json);
    }

    private IActionResult MapResult(UserOperationResult result) => result switch
    {
        UserOperationResult.NotFoundResult      => NotFound(new { error = "User not found" }),
        UserOperationResult.ForbiddenResult     => Forbid(),
        UserOperationResult.BadRequestResult  e => BadRequest(e.Payload),
        UserOperationResult.Success           s => Ok(s.Payload),
        _                                       => throw new InvalidOperationException("Unknown result"),
    };
}
