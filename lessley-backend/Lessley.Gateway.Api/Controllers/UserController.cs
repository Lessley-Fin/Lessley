using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Net.Mime;

namespace Lessley.Gateway.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
[Produces(MediaTypeNames.Application.Json)]
public class UserController : ControllerBase
{
    private readonly IUserService _userService;

    public UserController(IUserService userService)
    {
        _userService = userService;
    }

    /// <summary>Updates user settings: loyalty clubs, match level, or muted categories.</summary>
    /// <remarks>
    /// Admins may update any user; regular users may only update themselves.<br/>
    /// When muted categories change, SignalR group memberships are re-synced immediately.<br/>
    /// When match level or muted categories change, a full Personalization recalculation is triggered.
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
        var result = await _userService.UpdateAsync(email, dto, User, ct);
        return MapResult(result);
    }

    /// <summary>Triggers a full Personalization recalculation for a user's category tags.</summary>
    /// <remarks>Admin only. Personalization will post the new tag set back via PUT /api/user/{email}/tags.</remarks>
    /// <param name="email">The email address of the user.</param>
    [HttpPost("{email}/recalculate")]
    [Authorize(Roles = "Admin")]
    [ProducesResponseType(StatusCodes.Status202Accepted)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> RecalculateCategories(string email, CancellationToken ct = default)
    {
        var result = await _userService.RecalculateCategoriesAsync(email, ct);
        return result is UserOperationResult.NotFoundResult ? NotFound(new { error = "User not found" }) : Accepted();
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
        var result = await _userService.AssignTagsAsync(email, tags);
        return MapResult(result);
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
