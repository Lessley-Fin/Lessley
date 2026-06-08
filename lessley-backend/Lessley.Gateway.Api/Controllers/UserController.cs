using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;

namespace Lessley.Gateway.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class UserController : ControllerBase
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IUserTagService _userTagService;
    private readonly IPersonalizationService _personalizationService;
    private readonly ILogger<UserController> _logger;

    public UserController(
        UserManager<ApplicationUser> userManager,
        IUserTagService userTagService,
        IPersonalizationService personalizationService,
        ILogger<UserController> logger)
    {
        _userManager            = userManager;
        _userTagService         = userTagService;
        _personalizationService = personalizationService;
        _logger                 = logger;
    }

    /// <summary>
    /// Update user configuration (loyalty clubs, match level, muted categories).
    /// Admins may update any user; regular users may only update themselves.
    ///
    /// Step 1 — persist changes to DB.
    /// Step 2 — if mutedTags changed, immediately re-sync SignalR group memberships so the user
    ///           stops receiving notifications for newly muted categories without delay.
    /// Step 3 — if matchingScore or mutedTags changed, trigger Personalization recalculation
    ///           (Personalization posts back new tags → PUT /api/user/{email}/tags → SyncGroups).
    /// </summary>
    [HttpPatch("{email}")]
    public async Task<IActionResult> UpdateUser(string email, [FromBody] UpdateUserDto dto, CancellationToken ct = default)
    {
        var callerEmail = User.FindFirstValue(ClaimTypes.Email);
        var isAdmin     = User.IsInRole("Admin");

        if (!isAdmin && !string.Equals(callerEmail, email, StringComparison.OrdinalIgnoreCase))
            return Forbid();

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return NotFound(new { error = "User not found" });

        var matchChanged = dto.MatchingScore.HasValue && dto.MatchingScore != user.MatchingScore;
        var mutedChanged = dto.MutedTags is not null &&
            !(user.MutedTags ?? new()).OrderBy(t => t).SequenceEqual(dto.MutedTags.OrderBy(t => t));

        if (dto.MutedTags is not null)   user.MutedTags     = dto.MutedTags;
        if (dto.Clubs is not null)       user.Clubs         = dto.Clubs;
        if (dto.MatchingScore.HasValue)  user.MatchingScore = dto.MatchingScore.Value;

        // Step 1: persist to DB
        var result = await _userManager.UpdateAsync(user);
        if (!result.Succeeded)
            return BadRequest(result.Errors);

        // Step 2: muted tags changed → re-sync SignalR groups immediately.
        // previousTags == currentTags here (PATCH does not change Tags), so SyncGroupsAsync
        // removes the user from all their tag groups then re-adds only the non-muted ones.
        if (mutedChanged)
            await _userTagService.SyncGroupsAsync(user.Id, user.Tags ?? new List<string>(), ct);

        // Step 3: score or muted changed → trigger full category recalculation in Personalization.
        // Personalization will post the new tag set back to PUT /api/user/{email}/tags which
        // calls AssignTagsAsync → SyncGroupsAsync, completing the pipeline.
        if (matchChanged || mutedChanged)
        {
            try
            {
                await _personalizationService.RecalculateCategoriesAsync(email, ct);
            }
            catch (Exception ex)
            {
                // DB was saved and (if muted changed) groups were already synced.
                // Log and continue — the client should not get a 500 for a background failure.
                _logger.LogError(ex, "Category recalculation failed for {Email} — DB changes are saved", email);
            }
        }

        return Ok(new
        {
            email         = user.Email,
            tags          = user.Tags,
            mutedTags     = user.MutedTags,
            clubs         = user.Clubs,
            matchingScore = user.MatchingScore,
            recalculated  = matchChanged || mutedChanged,
        });
    }

    /// <summary>
    /// Explicitly trigger recalculation of the user's preferred categories.
    /// Personalization computes new categories and posts them back to PUT /api/user/{email}/tags,
    /// which persists the tags and re-syncs SignalR group memberships via SyncGroupsAsync.
    /// </summary>
    [HttpPost("{email}/recalculate")]
    public async Task<IActionResult> RecalculateCategories(string email, CancellationToken ct = default)
    {
        var callerEmail = User.FindFirstValue(ClaimTypes.Email);
        var isAdmin     = User.IsInRole("Admin");

        if (!isAdmin && !string.Equals(callerEmail, email, StringComparison.OrdinalIgnoreCase))
            return Forbid();

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return NotFound(new { error = "User not found" });

        await _personalizationService.RecalculateCategoriesAsync(email, ct);
        return Accepted(new { email = user.Email, message = "Category recalculation triggered" });
    }

    /// <summary>
    /// Assign tags to a user and update their SignalR group memberships.
    /// Admin only — tags drive deal category broadcasts and are not self-managed.
    /// </summary>
    [HttpPut("{email}/tags")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> UpdateUserTags(string email, [FromBody] string[] tags)
    {
        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return NotFound(new { error = "User not found" });

        await _userTagService.AssignTagsAsync(user.Id, tags);

        return Ok(new { email = user.Email, tags });
    }
}
