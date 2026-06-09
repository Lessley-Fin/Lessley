using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;
using System.Net.Mime;

namespace Lessley.Gateway.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
[Produces(MediaTypeNames.Application.Json)]
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

    /// <summary>Updates user settings: loyalty clubs, match level, or muted categories.</summary>
    /// <remarks>
    /// Admins may update any user; regular users may only update themselves.<br/>
    /// When muted categories change, SignalR group memberships are re-synced immediately.<br/>
    /// When match level or muted categories change, a full Personalization recalculation is triggered
    /// (Personalization posts new tags back to <c>PUT /api/user/{email}/tags</c>).
    /// </remarks>
    /// <param name="email">The email address of the user to update.</param>
    /// <param name="dto">Fields to update — all properties are optional.</param>
    [HttpPatch("{email}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
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

    /// <summary>Assigns category tags to a user and syncs their SignalR group memberships.</summary>
    /// <remarks>
    /// Admin only. Called internally by the Personalization service after recalculation.<br/>
    /// Tags control which deal-broadcast groups the user belongs to.
    /// </remarks>
    /// <param name="email">The email address of the user.</param>
    /// <param name="tags">The complete new set of category tags (replaces existing tags).</param>
    [HttpPut("{email}/tags")]
    [Authorize(Roles = "Admin")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> UpdateUserTags(string email, [FromBody] string[] tags)
    {
        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return NotFound(new { error = "User not found" });

        await _userTagService.AssignTagsAsync(user.Id, tags);

        return Ok(new { email = user.Email, tags });
    }
}
