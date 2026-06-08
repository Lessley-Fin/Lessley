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

    public UserController(
        UserManager<ApplicationUser> userManager,
        IUserTagService userTagService,
        IPersonalizationService personalizationService)
    {
        _userManager            = userManager;
        _userTagService         = userTagService;
        _personalizationService = personalizationService;
    }

    /// <summary>
    /// Process 3 — update user configuration (loyalty clubs, match level, muted categories).
    /// Admins may update any user; regular users may only update themselves.
    /// The user is addressed by email (the system-wide primary identifier) and resolved
    /// to their account here; internal services continue to key on user.Id.
    /// If the match level or muted categories changed, Process 2 (category recalculation) is
    /// triggered. Tags are managed separately via PUT /api/user/{email}/tags (Admin only).
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

        var result = await _userManager.UpdateAsync(user);
        if (!result.Succeeded)
            return BadRequest(result.Errors);

        // Process 2: a changed match level or muted categories requires recalculating the
        // preferred categories (Personalization writes the new tags back + regroups SignalR).
        if (matchChanged || mutedChanged)
            await _personalizationService.RecalculateCategoriesAsync(email, ct);

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
    /// Process 2 — explicitly trigger recalculation of the user's preferred categories based on
    /// their stored match level. Client → Gateway → Personalization; Personalization writes the
    /// new categories back to the Gateway and SignalR groups are updated if they changed.
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
    /// Assign tags to a user (addressed by email) and update their SignalR group memberships.
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
