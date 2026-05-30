namespace Lessley.Gateway.Api.Services.Interfaces;

/// <summary>
/// Manages the mapping of user IDs to their SignalR connection IDs.
/// Allows for efficient lookups of active connections per user.
/// </summary>
public interface IConnectionManager
{
    /// <summary>
    /// Registers a new connection for a user.
    /// </summary>
    /// <param name="userId">The user's unique identifier (from JWT NameIdentifier claim).</param>
    /// <param name="connectionId">The SignalR connection ID.</param>
    void AddConnection(string userId, string connectionId);

    /// <summary>
    /// Removes a connection for a user.
    /// </summary>
    /// <param name="userId">The user's unique identifier.</param>
    /// <param name="connectionId">The SignalR connection ID.</param>
    void RemoveConnection(string userId, string connectionId);

    /// <summary>
    /// Gets all active connection IDs for a specific user.
    /// </summary>
    /// <param name="userId">The user's unique identifier.</param>
    /// <returns>A list of connection IDs for the user, or an empty list if none exist.</returns>
    IEnumerable<string> GetConnections(string userId);

    /// <summary>
    /// Checks if a user has any active connections.
    /// </summary>
    /// <param name="userId">The user's unique identifier.</param>
    /// <returns>True if the user has at least one active connection; otherwise, false.</returns>
    bool HasConnections(string userId);
}
