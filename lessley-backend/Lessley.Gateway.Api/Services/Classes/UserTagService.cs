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
            // Throwing rather than returning: this runs inside a RabbitMQ consumer, so an
            // exception earns a redelivery while a log line loses the write silently. The
            // realistic cause is Identity's concurrency stamp rejecting the save because a
            // settings update landed between the read above and this line — precisely the
            // case a retry fixes, since the retry re-reads the user.
            var errors = string.Join("; ", result.Errors.Select(e => e.Description));
            _logger.LogError("AssignTags: DB update failed for user {Email}: {Errors}", email, errors);
            throw new InvalidOperationException($"Failed to assign tags to {email}: {errors}");
        }

        await SyncGroupsAsync(email, previousTags, ct);
        await NotifyCategoriesUpdatedAsync(email, user.Tags ?? new List<string>(), ct);
    }

    /// <summary>
    /// Tells any open tab that its cached categories are out of date.
    /// </summary>
    /// <remarks>
    /// Deliberately not a Notification: nothing is stored and nothing is shown. Recalculations
    /// are triggered by things the user did not ask for — a weekly sweep, a settings save
    /// rippling through — so surfacing them would be noise. This exists only so the client
    /// re-fetches instead of waiting out its cache.
    ///
    /// Sending to zero connections is the normal case, not a failure: the sweep runs at
    /// midnight and the bank journey navigates the browser away. Those clients pick the change
    /// up when they reconnect, which is why the client also invalidates on reconnect.
    /// </remarks>
    private async Task NotifyCategoriesUpdatedAsync(string email, IReadOnlyList<string> tags, CancellationToken ct)
    {
        var connections = _connectionManager.GetConnections(email).ToList();
        if (connections.Count == 0)
            return;

        var payload = new { timestamp = DateTime.UtcNow, tags };
        foreach (var connectionId in connections)
            await _hubContext.Clients.Client(connectionId).SendAsync("CategoriesUpdated", payload, ct);

        _logger.LogInformation(
            "CategoriesUpdated sent to {Email} ({Count} live connection(s))", email, connections.Count);
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
