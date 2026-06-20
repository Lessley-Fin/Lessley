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
    private readonly INotificationService _notificationService;

    public UserController(
        IUserService userService,
        IOpenFinanceService openFinanceService,
        IPersonalizationService personalizationService,
        IPersonalizationProxyService personalizationProxy,
        INotificationService notificationService)
    {
        _userService            = userService;
        _openFinanceService     = openFinanceService;
        _personalizationService = personalizationService;
        _personalizationProxy   = personalizationProxy;
        _notificationService    = notificationService;
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

    /// <summary>Calculates and returns the authenticated user's spending categories via Personalization.</summary>
    [HttpGet("insights/categories")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetInsightsCategories(
        [FromQuery] int? days = null,
        CancellationToken ct = default)
    {
        if (days.HasValue && (days.Value < 1 || days.Value > 365))
            return BadRequest(new { error = "days must be between 1 and 365" });

        var response = await _personalizationProxy.GetInsightsCategoriesAsync(CallerEmail(), days, ct);
        return await ProxyResponse(response, ct);
    }

    /// <summary>Calculates and returns the authenticated user's top spending accounts via Personalization.</summary>
    [HttpGet("insights/top-accounts")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetInsightsTopAccounts(
        [FromQuery] int? days = null,
        CancellationToken ct = default)
    {
        if (days.HasValue && (days.Value < 1 || days.Value > 365))
            return BadRequest(new { error = "days must be between 1 and 365" });

        var response = await _personalizationProxy.GetInsightsTopAccountsAsync(CallerEmail(), days, ct);
        return await ProxyResponse(response, ct);
    }

    /// <summary>Calculates and returns the authenticated user's top spending stores via Personalization.</summary>
    [HttpGet("insights/top-stores")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetInsightsTopStores(
        [FromQuery] int? days = null,
        CancellationToken ct = default)
    {
        if (days.HasValue && (days.Value < 1 || days.Value > 365))
            return BadRequest(new { error = "days must be between 1 and 365" });

        var response = await _personalizationProxy.GetInsightsTopStoresAsync(CallerEmail(), days, ct);
        return await ProxyResponse(response, ct);
    }

    /// <summary>Triggers a missed-savings analysis via Personalization (async — result stored in notifications).</summary>
    [HttpPost("recommendations/missed-savings")]
    [ProducesResponseType(StatusCodes.Status202Accepted)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status422UnprocessableEntity)]
    public async Task<IActionResult> TriggerMissedSavings(CancellationToken ct)
    {
        var check = await CheckUserHasCategories(ct);
        if (check is not null) return check;
        await _personalizationService.TriggerCalculateMissedSavingsAsync(CallerEmail(), ct);
        return Accepted();
    }

    /// <summary>Triggers a matching-clubs analysis via Personalization (async — result stored in notifications).</summary>
    [HttpPost("recommendations/matching-clubs")]
    [ProducesResponseType(StatusCodes.Status202Accepted)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status422UnprocessableEntity)]
    public async Task<IActionResult> TriggerMatchingClubs(CancellationToken ct)
    {
        var check = await CheckUserHasCategories(ct);
        if (check is not null) return check;
        await _personalizationService.TriggerCalculateMatchingClubsAsync(CallerEmail(), ct);
        return Accepted();
    }

    /// <summary>Returns the latest stored result for every recommendation type (null if not yet computed).</summary>
    [HttpGet("recommendations")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetRecommendations(CancellationToken ct)
    {
        var calcByType = await _notificationService.GetLatestCalcGroupedAsync(CallerEmail(), ct);

        static object? ToCalcResult(Notification? n) => n is null ? null : new
        {
            data         = n.Data is not null ? JsonSerializer.Deserialize<JsonElement>(n.Data) : (JsonElement?)null,
            calculatedAt = n.SentAt,
        };

        calcByType.TryGetValue("missed-savings", out var missedSavings);
        calcByType.TryGetValue("matching-clubs", out var matchingClubs);

        return Ok(new
        {
            missedSavings = ToCalcResult(missedSavings),
            matchingClubs = ToCalcResult(matchingClubs),
        });
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
            return UnprocessableEntity(new { error = "User has no categories yet. Call GET /api/user/insights/categories first." });
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
