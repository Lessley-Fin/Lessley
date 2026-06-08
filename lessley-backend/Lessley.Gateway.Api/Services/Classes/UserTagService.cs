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

        var previousTags = (user.Tags ?? new List<string>()).ToList();
        user.Tags = tags.ToList();

        var result = await _userManager.UpdateAsync(user);
        if (!result.Succeeded)
        {
            _logger.LogError(
                "AssignTags: DB update failed for user {UserId}: {Errors}",
                userId, string.Join("; ", result.Errors.Select(e => e.Description)));
            return;
        }

        await SyncGroupsAsync(userId, previousTags, ct);
    }

    public async Task SyncGroupsAsync(string userId, IReadOnlyList<string> previousTags, CancellationToken ct = default)
    {
        var user = await _userManager.FindByIdAsync(userId);
        if (user is null)
        {
            _logger.LogWarning("SyncGroups: user {UserId} not found", userId);
            return;
        }

        var currentTags = user.Tags ?? new List<string>();
        var mutedTags   = user.MutedTags ?? new List<string>();
        var connections = _connectionManager.GetConnections(userId).ToList();

        if (connections.Count == 0)
        {
            _logger.LogInformation("SyncGroups: user {UserId} has no active connections — skipping", userId);
            return;
        }

        foreach (var tag in previousTags)
            foreach (var connectionId in connections)
                await _hubContext.Groups.RemoveFromGroupAsync(connectionId, tag, ct);

        var activeTags = currentTags.Where(t => !mutedTags.Contains(t)).ToList();
        foreach (var tag in activeTags)
            foreach (var connectionId in connections)
                await _hubContext.Groups.AddToGroupAsync(connectionId, tag, ct);

        _logger.LogInformation(
            "Groups synced for user {UserId} — {Count} connection(s). Active: {Tags}",
            userId, connections.Count, string.Join(", ", activeTags));
    }
}
