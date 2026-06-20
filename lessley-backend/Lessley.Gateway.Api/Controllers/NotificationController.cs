using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
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
    private readonly INotificationService _notificationService;
    private readonly ILogger<NotificationController> _logger;

    public NotificationController(
        IConnectionManager connectionManager,
        INotificationService notificationService,
        ILogger<NotificationController> logger)
    {
        _connectionManager   = connectionManager;
        _notificationService = notificationService;
        _logger              = logger;
    }

    /// <summary>Retrieves all notifications for the authenticated user within the 90-day window.</summary>
    [HttpGet]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetUserNotifications(CancellationToken ct)
    {
        var notifications = await _notificationService.GetUserNotificationsAsync(CallerEmail(), ct);
        return Ok(notifications);
    }

    /// <summary>Returns the real-time SignalR connection status for the authenticated user.</summary>
    [HttpGet("connection")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public IActionResult GetUserConnectionStatus()
    {
        var email       = CallerEmail();
        var isConnected = _connectionManager.HasConnections(email);
        var connections = _connectionManager.GetConnections(email).ToList();

        return Ok(new
        {
            email,
            isConnected,
            connectionCount = connections.Count,
            connectionIds   = connections,
        });
    }

    /// <summary>Marks all of the authenticated user's notifications as read.</summary>
    [HttpPost("read-all")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> MarkAllAsRead(CancellationToken ct)
    {
        await _notificationService.MarkAllAsReadAsync(CallerEmail(), ct);
        return Ok(new { message = "All notifications marked as read" });
    }

    /// <summary>Marks a single notification as read.</summary>
    /// <param name="notificationId">The notification's MongoDB ObjectId.</param>
    [HttpPost("{notificationId}/read")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> MarkAsRead(string notificationId, CancellationToken ct)
    {
        if (!ObjectId.TryParse(notificationId, out var objId))
            return BadRequest(new { error = "Invalid notification ID" });

        var found = await _notificationService.MarkAsReadAsync(objId, CallerEmail(), ct);
        if (!found)
            return NotFound(new { error = "Notification not found for this user" });

        return Ok(new { message = "Notification marked as read" });
    }

    private string CallerEmail() => User.FindFirstValue(ClaimTypes.Email) ?? string.Empty;
}
