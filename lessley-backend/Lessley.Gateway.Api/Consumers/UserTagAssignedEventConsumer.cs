using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Hubs;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.SignalR;

namespace Lessley.Gateway.Api.Consumers;

public class UserTagAssignedEventConsumer : IConsumer<UserTagAssignedEvent>
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IConnectionManager _connectionManager;
    private readonly IHubContext<NotificationHub> _hubContext;
    private readonly ILogger<UserTagAssignedEventConsumer> _logger;

    public UserTagAssignedEventConsumer(
        UserManager<ApplicationUser> userManager,
        IConnectionManager connectionManager,
        IHubContext<NotificationHub> hubContext,
        ILogger<UserTagAssignedEventConsumer> logger)
    {
        _userManager       = userManager;
        _connectionManager = connectionManager;
        _hubContext        = hubContext;
        _logger            = logger;
    }

    public async Task Consume(ConsumeContext<UserTagAssignedEvent> context)
    {
        var (userId, tag) = (context.Message.UserId, context.Message.Tag);

        var user = await _userManager.FindByIdAsync(userId);
        if (user is null)
        {
            _logger.LogWarning("UserTagAssigned: user {UserId} not found — skipping", userId);
            return;
        }

        // Persist the tag if not already stored
        user.Tags ??= new List<string>();
        if (!user.Tags.Contains(tag))
        {
            user.Tags.Add(tag);
            await _userManager.UpdateAsync(user);
        }

        // Dynamically add any active connections to the SignalR group
        var connections = _connectionManager.GetConnections(userId).ToList();
        foreach (var connectionId in connections)
            await _hubContext.Groups.AddToGroupAsync(connectionId, tag);

        _logger.LogInformation(
            "Tag '{Tag}' assigned to user {UserId} — {Count} active connection(s) joined the group",
            tag, userId, connections.Count);
    }
}
