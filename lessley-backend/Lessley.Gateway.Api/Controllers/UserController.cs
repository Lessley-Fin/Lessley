using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;

namespace Lessley.Gateway.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize(Roles = "Admin")]
public class UserController : ControllerBase
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IUserTagService _userTagService;

    public UserController(UserManager<ApplicationUser> userManager, IUserTagService userTagService)
    {
        _userManager    = userManager;
        _userTagService = userTagService;
    }

    [HttpPut("{userId}")]
    public async Task<IActionResult> UpdateUser(string userId, [FromBody] UpdateUserDto dto)
    {
        var user = await _userManager.FindByIdAsync(userId);
        if (user is null)
            return NotFound(new { error = "User not found" });

        var tagsChanged = dto.Tags is not null
            && !new HashSet<string>(dto.Tags).SetEquals(new HashSet<string>(user.Tags ?? new List<string>()));

        if (dto.MutedTags is not null)    user.MutedTags    = dto.MutedTags;
        if (dto.Clubs is not null)        user.Clubs        = dto.Clubs;
        if (dto.MatchingScore.HasValue)   user.MatchingScore = dto.MatchingScore.Value;

        // Persist non-tag field changes first so AssignTagsAsync sees updated MutedTags
        var result = await _userManager.UpdateAsync(user);
        if (!result.Succeeded)
            return BadRequest(result.Errors);

        // Tag assignment handles SignalR group updates and tag persistence
        if (tagsChanged && dto.Tags is not null)
            await _userTagService.AssignTagsAsync(userId, dto.Tags.ToArray());

        // Re-fetch to return the final state
        user = await _userManager.FindByIdAsync(userId);

        return Ok(new
        {
            userId        = user!.Id,
            tags          = user.Tags,
            mutedTags     = user.MutedTags,
            clubs         = user.Clubs,
            matchingScore = user.MatchingScore,
        });
    }
}
