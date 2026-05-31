using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.SignalR;
using Lessley.Gateway.Api.Hubs;

namespace Lessley.Gateway.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class NotificationController : ControllerBase
{
    private readonly IHubContext<NotificationHub> _hubContext;
    private readonly IConnectionManager _connectionManager;
    private readonly ILogger<NotificationController> _logger;

    public NotificationController(
        IHubContext<NotificationHub> hubContext,
        IConnectionManager connectionManager,
        ILogger<NotificationController> logger)
    {
        _hubContext = hubContext;
        _connectionManager = connectionManager;
        _logger = logger;
    }

    [HttpPost("user/{userId}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> SendToUser(string userId, [FromBody] SendNotificationDto dto)
    {
        if (string.IsNullOrWhiteSpace(userId))
            return BadRequest(new { error = "User ID is required" });

        var connections = _connectionManager.GetConnections(userId).ToList();

        if (connections.Count == 0)
        {
            _logger.LogWarning("No active connections found for user {UserId}", userId);
            return NotFound(new { error = $"User {userId} is not connected" });
        }

        var payload = new { timestamp = DateTime.UtcNow, message = dto.Message, type = "notification" };

        foreach (var connectionId in connections)
            await _hubContext.Clients.Client(connectionId).SendAsync("ReceiveNotification", payload);

        _logger.LogInformation("Notification sent to user {UserId} ({ConnectionCount} connections): {Message}",
            userId, connections.Count, dto.Message);

        return Ok(new { message = "Notification sent successfully", recipientCount = connections.Count });
    }

    [HttpPost("group/{tag}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> SendToGroup(string tag, [FromBody] SendNotificationDto dto)
    {
        if (string.IsNullOrWhiteSpace(tag))
            return BadRequest(new { error = "Group tag is required" });

        var payload = new { timestamp = DateTime.UtcNow, message = dto.Message, type = "group_notification", group = tag };

        await _hubContext.Clients.Group(tag).SendAsync("ReceiveNotification", payload);

        _logger.LogInformation("Notification sent to group {Tag}: {Message}", tag, dto.Message);

        return Ok(new { message = "Notification sent to group successfully", group = tag });
    }

    [HttpGet("status/{userId}")]
    public IActionResult GetUserConnectionStatus(string userId)
    {
        if (string.IsNullOrWhiteSpace(userId))
        {
            return BadRequest(new { error = "User ID is required" });
        }

        var isConnected = _connectionManager.HasConnections(userId);
        var connections = _connectionManager.GetConnections(userId).ToList();

        return Ok(new
        {
            userId = userId,
            isConnected = isConnected,
            connectionCount = connections.Count,
            connectionIds = connections
        });
    }
}
