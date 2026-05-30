using Lessley.Gateway.Api.Services.Interfaces;
using System.Collections.Concurrent;

namespace Lessley.Gateway.Api.Services.Classes;

/// <summary>
/// Manages SignalR connections for users in-memory.
/// Thread-safe implementation using a concurrent dictionary.
/// </summary>
public class ConnectionManager : IConnectionManager
{
    private readonly ConcurrentDictionary<string, HashSet<string>> _userConnections = new();
    private readonly ILogger<ConnectionManager> _logger;

    public ConnectionManager(ILogger<ConnectionManager> logger)
    {
        _logger = logger;
    }

    public void AddConnection(string userId, string connectionId)
    {
        if (string.IsNullOrWhiteSpace(userId) || string.IsNullOrWhiteSpace(connectionId))
        {
            _logger.LogWarning("Attempted to add connection with null or empty userId or connectionId");
            return;
        }

        _userConnections.AddOrUpdate(userId,
            new HashSet<string> { connectionId },
            (key, existingSet) =>
            {
                existingSet.Add(connectionId);
                return existingSet;
            });

        _logger.LogInformation("Connection added for user {UserId}: {ConnectionId}", userId, connectionId);
    }

    public void RemoveConnection(string userId, string connectionId)
    {
        if (string.IsNullOrWhiteSpace(userId) || string.IsNullOrWhiteSpace(connectionId))
        {
            _logger.LogWarning("Attempted to remove connection with null or empty userId or connectionId");
            return;
        }

        if (_userConnections.TryGetValue(userId, out var connections))
        {
            connections.Remove(connectionId);

            if (connections.Count == 0)
            {
                _userConnections.TryRemove(userId, out _);
                _logger.LogInformation("All connections removed for user {UserId}", userId);
            }
            else
            {
                _logger.LogInformation("Connection removed for user {UserId}: {ConnectionId}", userId, connectionId);
            }
        }
    }

    public IEnumerable<string> GetConnections(string userId)
    {
        if (string.IsNullOrWhiteSpace(userId))
        {
            return Enumerable.Empty<string>();
        }

        if (_userConnections.TryGetValue(userId, out var connections))
        {
            return connections.ToList();
        }

        return Enumerable.Empty<string>();
    }

    public bool HasConnections(string userId)
    {
        if (string.IsNullOrWhiteSpace(userId))
        {
            return false;
        }

        return _userConnections.ContainsKey(userId) && _userConnections[userId].Count > 0;
    }
}
