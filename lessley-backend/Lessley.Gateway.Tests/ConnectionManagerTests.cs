using Lessley.Gateway.Api.Services.Classes;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace Lessley.Gateway.Tests;

public class ConnectionManagerTests
{
    private readonly ConnectionManager _sut = new(NullLogger<ConnectionManager>.Instance);

    // ── AddConnection ──────────────────────────────────────────────────────────

    [Fact]
    public void AddConnection_AddsUserAsConnected()
    {
        _sut.AddConnection("user-1", "conn-1");

        Assert.True(_sut.HasConnections("user-1"));
    }

    [Fact]
    public void AddConnection_SameUser_MultipleConnections_AddsAll()
    {
        _sut.AddConnection("user-1", "conn-1");
        _sut.AddConnection("user-1", "conn-2");

        Assert.Equal(2, _sut.GetConnections("user-1").Count());
    }

    [Fact]
    public void AddConnection_DuplicateConnectionId_DoesNotDuplicate()
    {
        _sut.AddConnection("user-1", "conn-1");
        _sut.AddConnection("user-1", "conn-1");

        Assert.Single(_sut.GetConnections("user-1"));
    }

    [Theory]
    [InlineData(null, "conn-1")]
    [InlineData("", "conn-1")]
    [InlineData("   ", "conn-1")]
    [InlineData("user-1", null)]
    [InlineData("user-1", "")]
    public void AddConnection_InvalidInput_DoesNotAddAndDoesNotThrow(string? userId, string? connectionId)
    {
        var ex = Record.Exception(() => _sut.AddConnection(userId!, connectionId!));

        Assert.Null(ex);
        if (!string.IsNullOrWhiteSpace(userId))
            Assert.False(_sut.HasConnections(userId));
    }

    // ── RemoveConnection ───────────────────────────────────────────────────────

    [Fact]
    public void RemoveConnection_LastConnection_UserIsNoLongerTracked()
    {
        _sut.AddConnection("user-1", "conn-1");

        _sut.RemoveConnection("user-1", "conn-1");

        Assert.False(_sut.HasConnections("user-1"));
    }

    [Fact]
    public void RemoveConnection_OneOfMany_LeavesRemainingConnections()
    {
        _sut.AddConnection("user-1", "conn-1");
        _sut.AddConnection("user-1", "conn-2");

        _sut.RemoveConnection("user-1", "conn-1");

        var remaining = _sut.GetConnections("user-1").ToList();
        Assert.Single(remaining);
        Assert.Equal("conn-2", remaining[0]);
    }

    [Fact]
    public void RemoveConnection_NonExistentUser_DoesNotThrow()
    {
        var ex = Record.Exception(() => _sut.RemoveConnection("ghost", "conn-1"));

        Assert.Null(ex);
    }

    [Theory]
    [InlineData(null, "conn-1")]
    [InlineData("user-1", null)]
    [InlineData("", "")]
    public void RemoveConnection_InvalidInput_DoesNotThrow(string? userId, string? connectionId)
    {
        var ex = Record.Exception(() => _sut.RemoveConnection(userId!, connectionId!));

        Assert.Null(ex);
    }

    // ── GetConnections ─────────────────────────────────────────────────────────

    [Fact]
    public void GetConnections_UnknownUser_ReturnsEmpty()
    {
        Assert.Empty(_sut.GetConnections("ghost"));
    }

    [Fact]
    public void GetConnections_NullUser_ReturnsEmpty()
    {
        Assert.Empty(_sut.GetConnections(null!));
    }

    [Fact]
    public void GetConnections_ReturnsSnapshotNotLiveReference()
    {
        _sut.AddConnection("user-1", "conn-1");
        var snapshot = _sut.GetConnections("user-1").ToList();

        _sut.AddConnection("user-1", "conn-2");

        // Snapshot captured before second Add must still have exactly 1 item
        Assert.Single(snapshot);
    }

    // ── HasConnections ─────────────────────────────────────────────────────────

    [Fact]
    public void HasConnections_UnknownUser_ReturnsFalse()
    {
        Assert.False(_sut.HasConnections("ghost"));
    }

    [Fact]
    public void HasConnections_NullUser_ReturnsFalse()
    {
        Assert.False(_sut.HasConnections(null!));
    }

    [Fact]
    public void HasConnections_AfterAllConnectionsRemoved_ReturnsFalse()
    {
        _sut.AddConnection("user-1", "conn-1");
        _sut.RemoveConnection("user-1", "conn-1");

        Assert.False(_sut.HasConnections("user-1"));
    }

    // ── Thread Safety ──────────────────────────────────────────────────────────

    [Fact]
    public async Task AddConnection_ConcurrentAccess_NoConnectionsLost()
    {
        const int userCount = 5;
        const int connectionsPerUser = 40;

        await Task.WhenAll(Enumerable
            .Range(0, userCount * connectionsPerUser)
            .Select(i => Task.Run(() => _sut.AddConnection($"user-{i % userCount}", $"conn-{i}"))));

        var total = Enumerable.Range(0, userCount)
            .Sum(i => _sut.GetConnections($"user-{i}").Count());

        Assert.Equal(userCount * connectionsPerUser, total);
    }

    [Fact]
    public async Task RemoveConnection_ConcurrentAccess_DoesNotThrow()
    {
        for (var i = 0; i < 100; i++)
            _sut.AddConnection("user-1", $"conn-{i}");

        await Task.WhenAll(Enumerable
            .Range(0, 100)
            .Select(i => Task.Run(() => _sut.RemoveConnection("user-1", $"conn-{i}"))));

        Assert.False(_sut.HasConnections("user-1"));
    }
}
