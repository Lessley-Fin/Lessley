using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
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
    private readonly ILogger<NotificationController> _logger;

    public NotificationController(
        IConnectionManager connectionManager,
        ISendNotificationService sendNotificationService,
        INotificationService notificationService,
        ILogger<NotificationController> logger)
    {
        _connectionManager       = connectionManager;
        _sendNotificationService = sendNotificationService;
        _notificationService     = notificationService;
        _logger                  = logger;
    }

    [HttpPost("user/{userId}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> SendToUser(string userId, [FromBody] SendNotificationDto dto)
    {
        if (string.IsNullOrWhiteSpace(userId))
            return BadRequest(new { error = "User ID is required" });

        if (!_connectionManager.HasConnections(userId))
        {
            _logger.LogWarning("No active connections for user {UserId}", userId);
            return NotFound(new { error = $"User {userId} is not connected" });
        }

        var recipientCount = await _sendNotificationService.SendToUserAsync(userId, dto.Message, dto.DealId);
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

    [HttpGet("status/{userId}")]
    public IActionResult GetUserConnectionStatus(string userId)
    {
        if (string.IsNullOrWhiteSpace(userId))
            return BadRequest(new { error = "User ID is required" });

        var isConnected = _connectionManager.HasConnections(userId);
        var connections = _connectionManager.GetConnections(userId).ToList();

        return Ok(new
        {
            userId,
            isConnected,
            connectionCount = connections.Count,
            connectionIds   = connections,
        });
    }

    [HttpGet("user/{userId}")]
    public async Task<IActionResult> GetUserNotifications(string userId, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(userId))
            return BadRequest(new { error = "User ID is required" });

        var notifications = await _notificationService.GetUserNotificationsAsync(userId, ct);
        return Ok(notifications);
    }

    [HttpPost("read/{userId}")]
    public async Task<IActionResult> MarkUserNotificationsAsRead(string userId, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(userId))
            return BadRequest(new { error = "User ID is required" });

        await _notificationService.MarkUserNotificationsAsReadAsync(userId, ct);
        return Ok(new { message = "All notifications marked as read" });
    }
}
