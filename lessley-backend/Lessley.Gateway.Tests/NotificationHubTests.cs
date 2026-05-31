using Lessley.Gateway.Api.Hubs;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.SignalR;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Xunit;

namespace Lessley.Gateway.Tests;

public class NotificationHubTests
{
    private readonly Mock<IConnectionManager> _connectionManager = new();

    // Hub.Context is a public settable property on the base Hub class,
    // so we can inject a mocked HubCallerContext directly.
    private NotificationHub BuildHub(string? userIdentifier, string connectionId)
    {
        var hub = new NotificationHub(NullLogger<NotificationHub>.Instance, _connectionManager.Object);

        var ctx = new Mock<HubCallerContext>();
        ctx.Setup(c => c.UserIdentifier).Returns(userIdentifier);
        ctx.Setup(c => c.ConnectionId).Returns(connectionId);
        hub.Context = ctx.Object;

        return hub;
    }

    // ── OnConnectedAsync ───────────────────────────────────────────────────────

    [Fact]
    public async Task OnConnectedAsync_AuthenticatedUser_RegistersConnection()
    {
        var hub = BuildHub("user-123", "conn-abc");

        await hub.OnConnectedAsync();

        _connectionManager.Verify(m => m.AddConnection("user-123", "conn-abc"), Times.Once);
    }

    [Fact]
    public async Task OnConnectedAsync_NullUserIdentifier_DoesNotRegister()
    {
        var hub = BuildHub(null, "conn-abc");

        await hub.OnConnectedAsync();

        _connectionManager.Verify(m => m.AddConnection(It.IsAny<string>(), It.IsAny<string>()), Times.Never);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public async Task OnConnectedAsync_BlankUserIdentifier_DoesNotRegister(string userId)
    {
        var hub = BuildHub(userId, "conn-abc");

        await hub.OnConnectedAsync();

        _connectionManager.Verify(m => m.AddConnection(It.IsAny<string>(), It.IsAny<string>()), Times.Never);
    }

    // ── OnDisconnectedAsync ────────────────────────────────────────────────────

    [Fact]
    public async Task OnDisconnectedAsync_AuthenticatedUser_DeregistersConnection()
    {
        var hub = BuildHub("user-123", "conn-abc");

        await hub.OnDisconnectedAsync(null);

        _connectionManager.Verify(m => m.RemoveConnection("user-123", "conn-abc"), Times.Once);
    }

    [Fact]
    public async Task OnDisconnectedAsync_WithException_StillDeregisters()
    {
        var hub = BuildHub("user-123", "conn-abc");

        await hub.OnDisconnectedAsync(new IOException("transport error"));

        _connectionManager.Verify(m => m.RemoveConnection("user-123", "conn-abc"), Times.Once);
    }

    [Fact]
    public async Task OnDisconnectedAsync_NullUserIdentifier_DoesNotDeregister()
    {
        var hub = BuildHub(null, "conn-abc");

        await hub.OnDisconnectedAsync(null);

        _connectionManager.Verify(m => m.RemoveConnection(It.IsAny<string>(), It.IsAny<string>()), Times.Never);
    }

    // ── Symmetry ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task ConnectThenDisconnect_ExactlyOneAddAndOneRemove()
    {
        var hub = BuildHub("user-123", "conn-abc");

        await hub.OnConnectedAsync();
        await hub.OnDisconnectedAsync(null);

        _connectionManager.Verify(m => m.AddConnection("user-123", "conn-abc"), Times.Once);
        _connectionManager.Verify(m => m.RemoveConnection("user-123", "conn-abc"), Times.Once);
    }
}
