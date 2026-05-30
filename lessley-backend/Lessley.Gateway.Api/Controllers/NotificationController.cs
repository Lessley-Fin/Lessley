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

    /// <summary>
    /// Sends a notification to a specific user.
    /// </summary>
    /// <param name="userId">The target user ID.</param>
    /// <param name="message">The notification message to send.</param>
    /// <returns>A response indicating success or failure.</returns>
    [HttpPost("user/{userId}")]
    public async Task<IActionResult> SendToUser(string userId, [FromQuery] string message)
    {
        if (string.IsNullOrWhiteSpace(userId))
        {
            return BadRequest(new { error = "User ID is required" });
        }

        if (string.IsNullOrWhiteSpace(message))
        {
            return BadRequest(new { error = "Message is required" });
        }

        try
        {
            var connections = _connectionManager.GetConnections(userId);
            
            if (!connections.Any())
            {
                _logger.LogWarning("No active connections found for user {UserId}", userId);
                return NotFound(new { error = $"User {userId} is not connected" });
            }

            var payload = new
            {
                timestamp = DateTime.UtcNow,
                message = message,
                type = "notification"
            };

            // Send to all connections for this user
            foreach (var connectionId in connections)
            {
                await _hubContext.Clients.Client(connectionId).SendAsync("ReceiveNotification", payload);
            }

            _logger.LogInformation("Notification sent to user {UserId} ({ConnectionCount} connections): {Message}", 
                userId, connections.Count(), message);

            return Ok(new 
            { 
                message = "Notification sent successfully", 
                recipientCount = connections.Count() 
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error sending notification to user {UserId}", userId);
            return StatusCode(500, new { error = "An error occurred while sending the notification" });
        }
    }

    /// <summary>
    /// Sends a notification to all users in a SignalR group (tag).
    /// </summary>
    /// <param name="tag">The group/tag name.</param>
    /// <param name="message">The notification message to send.</param>
    /// <returns>A response indicating success or failure.</returns>
    [HttpPost("group/{tag}")]
    public async Task<IActionResult> SendToGroup(string tag, [FromQuery] string message)
    {
        if (string.IsNullOrWhiteSpace(tag))
        {
            return BadRequest(new { error = "Group tag is required" });
        }

        if (string.IsNullOrWhiteSpace(message))
        {
            return BadRequest(new { error = "Message is required" });
        }

        try
        {
            var payload = new
            {
                timestamp = DateTime.UtcNow,
                message = message,
                type = "group_notification",
                group = tag
            };

            // Send to all users in the group
            await _hubContext.Clients.Group(tag).SendAsync("ReceiveNotification", payload);

            _logger.LogInformation("Notification sent to group {Tag}: {Message}", tag, message);

            return Ok(new 
            { 
                message = "Notification sent to group successfully", 
                group = tag 
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error sending notification to group {Tag}", tag);
            return StatusCode(500, new { error = "An error occurred while sending the notification" });
        }
    }

    /// <summary>
    /// Health check endpoint to verify if a user is currently connected.
    /// </summary>
    /// <param name="userId">The user ID to check.</param>
    /// <returns>Connection status information.</returns>
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
