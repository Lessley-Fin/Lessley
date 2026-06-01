using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.SignalR;

namespace Lessley.Gateway.Api.Hubs;

[Authorize]
public class NotificationHub : Hub
{
    private readonly ILogger<NotificationHub> _logger;
    private readonly IConnectionManager _connectionManager;
    private readonly UserManager<ApplicationUser> _userManager;

    public NotificationHub(
        ILogger<NotificationHub> logger,
        IConnectionManager connectionManager,
        UserManager<ApplicationUser> userManager)
    {
        _logger = logger;
        _connectionManager = connectionManager;
        _userManager = userManager;
    }

    public override async Task OnConnectedAsync()
    {
        var userId       = Context.UserIdentifier;
        var connectionId = Context.ConnectionId;

        _logger.LogInformation(
            "Client connected. ConnectionId: {ConnectionId}, UserId: {UserId}",
            connectionId, userId);

        if (!string.IsNullOrWhiteSpace(userId))
        {
            _connectionManager.AddConnection(userId, connectionId);

            // Rejoin all SignalR groups the user belongs to based on their stored tags
            var user = await _userManager.FindByIdAsync(userId);
            if (user?.Tags is { Count: > 0 })
            {
                foreach (var tag in user.Tags)
                    await Groups.AddToGroupAsync(connectionId, tag);

                _logger.LogInformation(
                    "User {UserId} added to {Count} group(s): {Tags}",
                    userId, user.Tags.Count, string.Join(", ", user.Tags));
            }
        }

        await base.OnConnectedAsync();
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        var userId       = Context.UserIdentifier;
        var connectionId = Context.ConnectionId;

        _logger.LogInformation(
            exception,
            "Client disconnected. ConnectionId: {ConnectionId}, UserId: {UserId}",
            connectionId, userId);

        if (!string.IsNullOrWhiteSpace(userId))
            _connectionManager.RemoveConnection(userId, connectionId);

        // SignalR automatically removes the connection from all groups on disconnect
        await base.OnDisconnectedAsync(exception);
    }
}
