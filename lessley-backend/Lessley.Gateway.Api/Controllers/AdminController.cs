using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Net.Mime;

namespace Lessley.Gateway.Api.Controllers;

[Route("api/[controller]")]
[ApiController]
[Authorize(Roles = nameof(UserRoles.Admin))]
[Produces(MediaTypeNames.Application.Json)]
public class AdminController : ControllerBase
{
    private readonly IConfiguration _configuration;
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly ApplicationDbContext _context;
    private readonly IUserService _userService;
    private readonly ISendNotificationService _sendNotificationService;

    public AdminController(
        IConfiguration configuration,
        UserManager<ApplicationUser> userManager,
        ApplicationDbContext context,
        IUserService userService,
        ISendNotificationService sendNotificationService)
    {
        _configuration           = configuration;
        _userManager             = userManager;
        _context                 = context;
        _userService             = userService;
        _sendNotificationService = sendNotificationService;
    }

    /// <summary>One-time admin bootstrap. Creates the initial admin user from app configuration.</summary>
    /// <remarks>Fails if any users already exist, preventing repeated bootstrapping.</remarks>
    /// <param name="key">Secret key configured in <c>Bootstrap:Key</c> — required when set.</param>
    [AllowAnonymous]
    [HttpPost("bootstrap")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> Bootstrap([FromQuery] string? key = null)
    {
        // Fail closed: with no key configured, bootstrap is disabled entirely rather than
        // left open to the first anonymous caller.
        var bootstrapKey = _configuration["Bootstrap:Key"];
        if (string.IsNullOrEmpty(bootstrapKey))
            return StatusCode(StatusCodes.Status503ServiceUnavailable, "Bootstrap is disabled: no Bootstrap:Key configured.");
        if (key != bootstrapKey)
            return Unauthorized("Invalid bootstrap key");

        var count = await _userManager.Users.CountAsync();
        if (count > 0)
            return BadRequest("Bootstrap already completed.");

        var username = _configuration["Bootstrap:Username"] ?? "";
        var password = _configuration["Bootstrap:Password"] ?? "";
        var email    = _configuration["Bootstrap:Email"]    ?? "";

        if (username == "" || password == "" || email == "")
            return BadRequest("Bootstrap configuration is incomplete.");

        var user = new ApplicationUser
        {
            UserName = username,
            Email    = email,
            Clubs    = new(),
        };
        var result = await _userManager.CreateAsync(user, password);
        if (!result.Succeeded) return BadRequest(result.Errors);

        result = await _userManager.AddToRoleAsync(user, UserRoles.Admin.ToString());
        if (!result.Succeeded) return BadRequest(result.Errors);

        return Ok();
    }

    /// <summary>Changes a user's role.</summary>
    [HttpPut("role/{email}/{newRole}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> ChangeUserRole([FromRoute] string email, [FromRoute] UserRoles newRole)
    {
        var user = await _userManager.FindByEmailAsync(email);
        if (user == null) return NotFound("User not found");

        var userRoleIds = await _context.UserRoles
            .Where(ur => ur.UserId == user.Id)
            .Select(ur => ur.RoleId)
            .ToListAsync();

        var currentRoles = await _context.Roles
            .Where(r => userRoleIds.Contains(r.Id))
            .Select(r => r.Name!)
            .ToListAsync();

        await _userManager.RemoveFromRolesAsync(user, currentRoles);
        await _userManager.AddToRoleAsync(user, newRole.ToString());

        return Ok($"User role changed to {newRole}");
    }

    /// <summary>Assigns category tags to a user and syncs their SignalR group memberships.</summary>
    /// <remarks>Called internally by the Personalization service after recalculation.</remarks>
    [HttpPut("users/{email}/tags")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> UpdateUserTags([FromRoute] string email, [FromBody] string[] tags)
    {
        var result = await _userService.AssignTagsAsync(email, tags);
        return MapResult(result);
    }

    /// <summary>Sends a direct notification to a specific user. Admin only.</summary>
    [HttpPost("notifications/user/{email}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> SendNotificationToUser([FromRoute] string email, [FromBody] SendNotificationDto dto)
    {
        if (string.IsNullOrWhiteSpace(email))
            return BadRequest(new { error = "User email is required" });

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return NotFound(new { error = $"User {email} not found" });

        var recipientCount = await _sendNotificationService.SendToUserAsync(email, dto.Message, dto.DealId);
        return Ok(new { message = "Notification sent successfully", recipientCount });
    }

    /// <summary>Broadcasts a notification to all users subscribed to the given category tag. Admin only.</summary>
    [HttpPost("notifications/group/{tag}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    public async Task<IActionResult> SendNotificationToGroup([FromRoute] string tag, [FromBody] SendNotificationDto dto)
    {
        if (string.IsNullOrWhiteSpace(tag))
            return BadRequest(new { error = "Group tag is required" });

        await _sendNotificationService.SendToGroupAsync(tag, dto.Message, dto.DealId);
        return Ok(new { message = "Notification sent to group successfully", group = tag });
    }

    /// <summary>Broadcasts a notification to every user. Admin only.</summary>
    [HttpPost("notifications/broadcast")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    public async Task<IActionResult> SendNotificationToAll([FromBody] BroadcastNotificationDto dto)
    {
        var recipientCount = await _sendNotificationService.SendToAllAsync(dto.Message);
        return Ok(new { message = "Notification broadcast to all users", recipientCount });
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
