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

    public UserController(UserManager<ApplicationUser> userManager, IUserTagService userTagService)
    {
        _userManager    = userManager;
        _userTagService = userTagService;
    }

    /// <summary>
    /// Update own preferences (MutedTags, Clubs, MatchingScore).
    /// Admins may update any user; regular users may only update themselves.
    /// Tags are managed separately via PUT /api/user/{userId}/tags (Admin only).
    /// </summary>
    [HttpPut("{userId}")]
    public async Task<IActionResult> UpdateUser(string userId, [FromBody] UpdateUserDto dto)
    {
        var callerId = User.FindFirstValue(ClaimTypes.NameIdentifier);
        var isAdmin  = User.IsInRole("Admin");

        if (!isAdmin && callerId != userId)
            return Forbid();

        var user = await _userManager.FindByIdAsync(userId);
        if (user is null)
            return NotFound(new { error = "User not found" });

        if (dto.MutedTags is not null)   user.MutedTags    = dto.MutedTags;
        if (dto.Clubs is not null)       user.Clubs        = dto.Clubs;
        if (dto.MatchingScore.HasValue)  user.MatchingScore = dto.MatchingScore.Value;

        var result = await _userManager.UpdateAsync(user);
        if (!result.Succeeded)
            return BadRequest(result.Errors);

        return Ok(new
        {
            userId        = user.Id,
            tags          = user.Tags,
            mutedTags     = user.MutedTags,
            clubs         = user.Clubs,
            matchingScore = user.MatchingScore,
        });
    }

    /// <summary>
    /// Assign tags to a user and update their SignalR group memberships.
    /// Admin only — tags drive deal category broadcasts and are not self-managed.
    /// </summary>
    [HttpPut("{userId}/tags")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> UpdateUserTags(string userId, [FromBody] string[] tags)
    {
        var user = await _userManager.FindByIdAsync(userId);
        if (user is null)
            return NotFound(new { error = "User not found" });

        await _userTagService.AssignTagsAsync(userId, tags);

        return Ok(new { userId, tags });
    }
}
