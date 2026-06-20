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

    public async Task AssignTagsAsync(string email, string[] tags, CancellationToken ct = default)
    {
        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
        {
            _logger.LogWarning("AssignTags: user {Email} not found — skipping", email);
            return;
        }

        var previousTags = (user.Tags ?? new List<string>()).ToList();
        user.Tags = tags.ToList();

        var result = await _userManager.UpdateAsync(user);
        if (!result.Succeeded)
        {
            _logger.LogError(
                "AssignTags: DB update failed for user {Email}: {Errors}",
                email, string.Join("; ", result.Errors.Select(e => e.Description)));
            return;
        }

        await SyncGroupsAsync(email, previousTags, ct);
    }

    public async Task SyncGroupsAsync(string email, IReadOnlyList<string> previousTags, CancellationToken ct = default)
    {
        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
        {
            _logger.LogWarning("SyncGroups: user {Email} not found", email);
            return;
        }

        var currentTags = user.Tags ?? new List<string>();
        var mutedTags   = user.MutedTags ?? new List<string>();
        var connections = _connectionManager.GetConnections(email).ToList();

        if (connections.Count == 0)
        {
            _logger.LogInformation("SyncGroups: user {Email} has no active connections — skipping", email);
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
            "Groups synced for user {Email} — {Count} connection(s). Active: {Tags}",
            email, connections.Count, string.Join(", ", activeTags));
    }
}
