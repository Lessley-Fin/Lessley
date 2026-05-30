using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.SignalR;
using Lessley.Gateway.Api.Services.Interfaces;

namespace Lessley.Gateway.Api.Hubs;

[Authorize]
public class NotificationHub : Hub
{
    private readonly ILogger<NotificationHub> _logger;
    private readonly IConnectionManager _connectionManager;

    public NotificationHub(ILogger<NotificationHub> logger, IConnectionManager connectionManager)
    {
        _logger = logger;
        _connectionManager = connectionManager;
    }

    public override async Task OnConnectedAsync()
    {
        var userId = Context.UserIdentifier;
        var connectionId = Context.ConnectionId;

        _logger.LogInformation("Client connected to NotificationHub. ConnectionId: {ConnectionId}, UserId: {UserId}", connectionId, userId);

        if (!string.IsNullOrWhiteSpace(userId))
        {
            _connectionManager.AddConnection(userId, connectionId);
        }

        await base.OnConnectedAsync();
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        var userId = Context.UserIdentifier;
        var connectionId = Context.ConnectionId;

        _logger.LogInformation(exception, "Client disconnected from NotificationHub. ConnectionId: {ConnectionId}, UserId: {UserId}", connectionId, userId);

        if (!string.IsNullOrWhiteSpace(userId))
        {
            _connectionManager.RemoveConnection(userId, connectionId);
        }

        await base.OnDisconnectedAsync(exception);
    }
}
