using Lessley.Gateway.Api.Services.Interfaces;
using System.Collections.Concurrent;

namespace Lessley.Gateway.Api.Services.Classes;

public class ConnectionManager : IConnectionManager
{
    // Inner dict: connectionId -> 0 (byte used as valueless placeholder).
    // ConcurrentDictionary<K,V> is fully thread-safe; HashSet is not.
    private readonly ConcurrentDictionary<string, ConcurrentDictionary<string, byte>> _userConnections = new();
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

        var connections = _userConnections.GetOrAdd(userId, _ => new ConcurrentDictionary<string, byte>());
        connections.TryAdd(connectionId, 0);

        _logger.LogInformation("Connection added for user {UserId}: {ConnectionId}", userId, connectionId);
    }

    public void RemoveConnection(string userId, string connectionId)
    {
        if (string.IsNullOrWhiteSpace(userId) || string.IsNullOrWhiteSpace(connectionId))
        {
            _logger.LogWarning("Attempted to remove connection with null or empty userId or connectionId");
            return;
        }

        if (!_userConnections.TryGetValue(userId, out var connections))
            return;

        connections.TryRemove(connectionId, out _);

        if (connections.IsEmpty)
        {
            _userConnections.TryRemove(userId, out _);
            _logger.LogInformation("All connections removed for user {UserId}", userId);
        }
        else
        {
            _logger.LogInformation("Connection removed for user {UserId}: {ConnectionId}", userId, connectionId);
        }
    }

    public IEnumerable<string> GetConnections(string userId)
    {
        if (string.IsNullOrWhiteSpace(userId))
            return Enumerable.Empty<string>();

        return _userConnections.TryGetValue(userId, out var connections)
            ? connections.Keys.ToList()
            : Enumerable.Empty<string>();
    }

    public bool HasConnections(string userId)
    {
        if (string.IsNullOrWhiteSpace(userId))
            return false;

        return _userConnections.TryGetValue(userId, out var connections) && !connections.IsEmpty;
    }
}
