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
        var email        = Context.UserIdentifier;
        var connectionId = Context.ConnectionId;

        _logger.LogInformation(
            "Client connected. ConnectionId: {ConnectionId}, Email: {Email}",
            connectionId, email);

        if (!string.IsNullOrWhiteSpace(email))
        {
            _connectionManager.AddConnection(email, connectionId);

            var user = await _userManager.FindByEmailAsync(email);
            if (user?.Tags is { Count: > 0 })
            {
                var mutedTags  = user.MutedTags ?? new List<string>();
                var activeTags = user.Tags.Where(t => !mutedTags.Contains(t)).ToList();

                foreach (var tag in activeTags)
                    await Groups.AddToGroupAsync(connectionId, tag);

                _logger.LogInformation(
                    "User {Email} added to {Count} group(s): {Tags}",
                    email, activeTags.Count, string.Join(", ", activeTags));
            }
        }

        await base.OnConnectedAsync();
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        var email        = Context.UserIdentifier;
        var connectionId = Context.ConnectionId;

        _logger.LogInformation(
            exception,
            "Client disconnected. ConnectionId: {ConnectionId}, Email: {Email}",
            connectionId, email);

        if (!string.IsNullOrWhiteSpace(email))
            _connectionManager.RemoveConnection(email, connectionId);

        // SignalR automatically removes the connection from all groups on disconnect
        await base.OnDisconnectedAsync(exception);
    }
}
