using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using System.Net.Mime;

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

    /// <summary>Sends a direct notification to a specific user.</summary>
    /// <remarks>
    /// Admin only. The notification is persisted to MongoDB even if the user is currently offline,
    /// so they will see it the next time they call <c>GET /api/notification/user/{email}</c>.
    /// </remarks>
    /// <param name="email">The recipient's email address.</param>
    /// <param name="dto">The notification payload (message and optional deal ID).</param>
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

        // Process 9: targeted delivery to a specific user regardless of category groups. The
        // notification is persisted even if the user is currently offline (recipientCount = 0).
        var recipientCount = await _sendNotificationService.SendToUserAsync(user.Id, dto.Message, dto.DealId);
        return Ok(new { message = "Notification sent successfully", recipientCount });
    }

    /// <summary>Broadcasts a notification to all users subscribed to the given category tag.</summary>
    /// <remarks>
    /// Admin only. Delivers via SignalR to all online users in the group and persists
    /// the notification so offline users retrieve it later. Muted users are excluded at
    /// connection time (they are never added to the SignalR group for their muted categories).
    /// </remarks>
    /// <param name="tag">The category tag identifying the target group (e.g. <c>MCC_5411</c>).</param>
    /// <param name="dto">The notification payload (message and optional deal ID).</param>
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
    /// <param name="email">The user's email address.</param>
    [HttpGet("status/{email}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetUserConnectionStatus(string email)
    {
        if (string.IsNullOrWhiteSpace(email))
            return BadRequest(new { error = "User email is required" });

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

    /// <summary>Retrieves all notifications for a user (both read and unread).</summary>
    /// <remarks>
    /// Returns direct user notifications and group notifications for the user's active category tags.
    /// Notifications for muted categories are automatically excluded from the result.
    /// </remarks>
    /// <param name="email">The user's email address.</param>
    [HttpGet("user/{email}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetUserNotifications(string email, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(email))
            return BadRequest(new { error = "User email is required" });

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return NotFound(new { error = $"User {email} not found" });

        var notifications = await _notificationService.GetUserNotificationsAsync(user.Id, ct);
        return Ok(notifications);
    }

    /// <summary>Marks all direct notifications for a user as read.</summary>
    /// <remarks>Only direct (user-targeted) notifications are marked; group notifications have no per-user read state.</remarks>
    /// <param name="email">The user's email address.</param>
    [HttpPost("read/{email}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> MarkUserNotificationsAsRead(string email, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(email))
            return BadRequest(new { error = "User email is required" });

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return NotFound(new { error = $"User {email} not found" });

        await _notificationService.MarkUserNotificationsAsReadAsync(user.Id, ct);
        return Ok(new { message = "All notifications marked as read" });
    }
}
