using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;

namespace Lessley.Gateway.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
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

    [HttpPost("user/{email}")]
    [Authorize(Roles = "Admin")]
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

    [HttpPost("group/{tag}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> SendToGroup(string tag, [FromBody] SendNotificationDto dto)
    {
        if (string.IsNullOrWhiteSpace(tag))
            return BadRequest(new { error = "Group tag is required" });

        await _sendNotificationService.SendToGroupAsync(tag, dto.Message, dto.DealId);
        return Ok(new { message = "Notification sent to group successfully", group = tag });
    }

    [HttpGet("status/{email}")]
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

    [HttpGet("user/{email}")]
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

    [HttpPost("read/{email}")]
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
