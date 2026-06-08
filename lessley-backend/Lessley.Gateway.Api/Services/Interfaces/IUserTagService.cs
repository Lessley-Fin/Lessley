namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IUserTagService
{
    /// <summary>
    /// Persists new tags to the user record and re-syncs all active SignalR group memberships.
    /// </summary>
    Task AssignTagsAsync(string userId, string[] tags, CancellationToken ct = default);

    /// <summary>
    /// Re-syncs SignalR group memberships after the DB has already been updated.
    /// Removes all connections from every group in <paramref name="previousTags"/>, then adds
    /// them to the user's current non-muted tags (read fresh from DB).
    /// No-op when the user has no active connections.
    /// </summary>
    Task SyncGroupsAsync(string userId, IReadOnlyList<string> previousTags, CancellationToken ct = default);
}
