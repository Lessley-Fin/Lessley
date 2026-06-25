using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using MongoDB.Bson;
using System.Net.Mime;
using System.Security.Claims;

namespace Lessley.Gateway.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
[Produces(MediaTypeNames.Application.Json)]
public class NotificationController : ControllerBase
{
    private readonly IConnectionManager _connectionManager;
    private readonly ISendNotificationService _sendNotificationService;
    private readonly INotificationService _notificationService;
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly ILogger<NotificationController> _logger;

    public NotificationController(
        IConnectionManager connectionManager,
        ISendNotificationService sendNotificationService,
        INotificationService notificationService,
        UserManager<ApplicationUser> userManager,
        ILogger<NotificationController> logger)
    {
        _connectionManager       = connectionManager;
        _sendNotificationService = sendNotificationService;
        _notificationService     = notificationService;
        _userManager             = userManager;
        _logger                  = logger;
    }

    // Users are addressed by email (the system-wide primary identifier); SignalR connections
    // and notification records are keyed on user.Id, so we resolve email -> user here.

    // Admins may act on any user; everyone else only on their own (email-claim) data.
    private bool IsCallerAllowed(string email) =>
        User.IsInRole("Admin")
        || string.Equals(User.FindFirstValue(ClaimTypes.Email), email, StringComparison.OrdinalIgnoreCase);

    /// <summary>Sends a direct notification to a specific user.</summary>
    /// <remarks>
    /// Admin only. Persisted to MongoDB even if the user is offline and creates a
    /// notification_read record so the user will see it on next login.
    /// </remarks>
    [HttpPost("user/{email}")]
    [Authorize(Roles = "Admin")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> SendToUser(string email, [FromBody] SendNotificationDto dto)
    {
        if (string.IsNullOrWhiteSpace(email))
            return BadRequest(new { error = "User email is required" });

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return NotFound(new { error = $"User {email} not found" });

        var recipientCount = await _sendNotificationService.SendToUserAsync(user.Id, dto.Message, dto.DealId);
        return Ok(new { message = "Notification sent successfully", recipientCount });
    }

    /// <summary>Broadcasts a notification to all users subscribed to the given category tag.</summary>
    /// <remarks>
    /// Admin only. Delivers via SignalR to online users and creates a notification_read record
    /// for every user who currently has this tag (including offline users).
    /// </remarks>
    [HttpPost("group/{tag}")]
    [Authorize(Roles = "Admin")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    public async Task<IActionResult> SendToGroup(string tag, [FromBody] SendNotificationDto dto)
    {
        if (string.IsNullOrWhiteSpace(tag))
            return BadRequest(new { error = "Group tag is required" });

        await _sendNotificationService.SendToGroupAsync(tag, dto.Message, dto.DealId);
        return Ok(new { message = "Notification sent to group successfully", group = tag });
    }

    /// <summary>Returns the real-time SignalR connection status for a user.</summary>
    [HttpGet("status/{email}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetUserConnectionStatus(string email)
    {
        if (string.IsNullOrWhiteSpace(email))
            return BadRequest(new { error = "User email is required" });

        if (!IsCallerAllowed(email))
            return Forbid();

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return NotFound(new { error = $"User {email} not found" });

        var isConnected = _connectionManager.HasConnections(user.Id);
        var connections = _connectionManager.GetConnections(user.Id).ToList();

        return Ok(new
        {
            email,
            isConnected,
            connectionCount = connections.Count,
            connectionIds   = connections,
        });
    }

    /// <summary>Retrieves all notifications for a user within the 90-day window.</summary>
    /// <remarks>
    /// Returns notifications the user received at send-time (based on their tags when each
    /// notification was sent) plus any direct notifications. Preserves history across tag changes.
    /// </remarks>
    [HttpGet("user/{email}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetUserNotifications(string email, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(email))
            return BadRequest(new { error = "User email is required" });

        if (!IsCallerAllowed(email))
            return Forbid();

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return NotFound(new { error = $"User {email} not found" });

        var notifications = await _notificationService.GetUserNotificationsAsync(user.Id, ct);
        return Ok(notifications);
    }

    /// <summary>Marks all of a user's notifications as read.</summary>
    [HttpPost("read/{email}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> MarkAllAsRead(string email, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(email))
            return BadRequest(new { error = "User email is required" });

        if (!IsCallerAllowed(email))
            return Forbid();

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return NotFound(new { error = $"User {email} not found" });

        await _notificationService.MarkAllAsReadAsync(user.Id, ct);
        return Ok(new { message = "All notifications marked as read" });
    }

    /// <summary>Marks a single notification as read for the given user.</summary>
    /// <param name="notificationId">The notification's ID (from the GET response).</param>
    /// <param name="email">The user's email address.</param>
    [HttpPost("{notificationId}/read/{email}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> MarkAsRead(string notificationId, string email, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(email))
            return BadRequest(new { error = "User email is required" });

        if (!IsCallerAllowed(email))
            return Forbid();

        if (!ObjectId.TryParse(notificationId, out var objId))
            return BadRequest(new { error = "Invalid notification ID" });

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return NotFound(new { error = $"User {email} not found" });

        var found = await _notificationService.MarkAsReadAsync(objId, user.Id, ct);
        if (!found)
            return NotFound(new { error = "Notification not found for this user" });

        return Ok(new { message = "Notification marked as read" });
    }
}
