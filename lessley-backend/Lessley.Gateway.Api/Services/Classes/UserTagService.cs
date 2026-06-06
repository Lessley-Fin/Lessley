using Lessley.Gateway.Api.Hubs;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.SignalR;

namespace Lessley.Gateway.Api.Services.Classes;

public class UserTagService : IUserTagService
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IConnectionManager _connectionManager;
    private readonly IHubContext<NotificationHub> _hubContext;
    private readonly ILogger<UserTagService> _logger;

    public UserTagService(
        UserManager<ApplicationUser> userManager,
        IConnectionManager connectionManager,
        IHubContext<NotificationHub> hubContext,
        ILogger<UserTagService> logger)
    {
        _userManager       = userManager;
        _connectionManager = connectionManager;
        _hubContext        = hubContext;
        _logger            = logger;
    }

    public async Task AssignTagsAsync(string userId, string[] tags, CancellationToken ct = default)
    {
        var user = await _userManager.FindByIdAsync(userId);
        if (user is null)
        {
            _logger.LogWarning("AssignTags: user {UserId} not found — skipping", userId);
            return;
        }

        var previousTags = user.Tags ?? new List<string>();
        var mutedTags    = user.MutedTags ?? new List<string>();
        var newTags      = tags.ToList();

        user.Tags = newTags;
        await _userManager.UpdateAsync(user);

        var connections = _connectionManager.GetConnections(userId).ToList();
        if (connections.Count == 0)
        {
            _logger.LogInformation("Tags assigned to offline user {UserId}: {Tags}", userId, string.Join(", ", tags));
            return;
        }

        // Remove connections from all previous tag groups
        foreach (var oldTag in previousTags)
            foreach (var connectionId in connections)
                await _hubContext.Groups.RemoveFromGroupAsync(connectionId, oldTag, ct);

        // Add connections to new non-muted tag groups
        var activeTags = newTags.Where(t => !mutedTags.Contains(t)).ToList();
        foreach (var tag in activeTags)
            foreach (var connectionId in connections)
                await _hubContext.Groups.AddToGroupAsync(connectionId, tag, ct);

        _logger.LogInformation(
            "Tags assigned to user {UserId} — {Count} connection(s) updated. Active groups: {Tags}",
            userId, connections.Count, string.Join(", ", activeTags));
    }
}
