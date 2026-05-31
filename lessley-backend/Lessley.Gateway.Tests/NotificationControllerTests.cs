using System.Text.Json;
using Lessley.Gateway.Api.Controllers;
using Xunit;
using Lessley.Gateway.Api.Hubs;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.SignalR;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;

namespace Lessley.Gateway.Tests;

public class NotificationControllerTests
{
    private readonly Mock<IConnectionManager> _connectionManager = new();
    private readonly Mock<INotificationStore> _notificationStore = new();
    // In ASP.NET Core 8, IHubClients.Client() returns ISingleClientProxy (extends IClientProxy),
    // while Group() returns the base IClientProxy.
    private readonly Mock<ISingleClientProxy> _singleClientProxy = new();
    private readonly Mock<IClientProxy> _groupProxy = new();
    private readonly Mock<IHubClients> _hubClients = new();
    private readonly Mock<IHubContext<NotificationHub>> _hubContext = new();
    private readonly NotificationController _controller;

    public NotificationControllerTests()
    {
        // SendAsync is an extension over SendCoreAsync — mock the core method.
        _singleClientProxy
            .Setup(p => p.SendCoreAsync(It.IsAny<string>(), It.IsAny<object[]>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        _groupProxy
            .Setup(p => p.SendCoreAsync(It.IsAny<string>(), It.IsAny<object[]>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        _hubClients.Setup(c => c.Client(It.IsAny<string>())).Returns(_singleClientProxy.Object);
        _hubClients.Setup(c => c.Group(It.IsAny<string>())).Returns(_groupProxy.Object);
        _hubContext.Setup(h => h.Clients).Returns(_hubClients.Object);

        _notificationStore
            .Setup(s => s.SaveAsync(It.IsAny<Notification>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        _controller = new NotificationController(
            _hubContext.Object,
            _connectionManager.Object,
            _notificationStore.Object,
            NullLogger<NotificationController>.Instance);
    }

    // ── SendToUser ─────────────────────────────────────────────────────────────

    [Fact]
    public async Task SendToUser_UserHasConnections_SendsToEachConnectionAndReturns200()
    {
        _connectionManager
            .Setup(m => m.GetConnections("user-1"))
            .Returns(new[] { "conn-a", "conn-b" });

        var result = await _controller.SendToUser("user-1", new SendNotificationDto("Hello"));

        var ok = Assert.IsType<OkObjectResult>(result);
        _hubClients.Verify(c => c.Client(It.IsAny<string>()), Times.Exactly(2));
        _singleClientProxy.Verify(
            p => p.SendCoreAsync("ReceiveNotification", It.IsAny<object[]>(), It.IsAny<CancellationToken>()),
            Times.Exactly(2));
        var json = JsonSerializer.Serialize(ok.Value);
        var doc = JsonDocument.Parse(json);
        Assert.Equal(2, doc.RootElement.GetProperty("recipientCount").GetInt32());
    }

    [Fact]
    public async Task SendToUser_UserHasConnections_SavesNotificationToStore()
    {
        _connectionManager
            .Setup(m => m.GetConnections("user-1"))
            .Returns(new[] { "conn-a" });

        await _controller.SendToUser("user-1", new SendNotificationDto("Hello"));

        _notificationStore.Verify(
            s => s.SaveAsync(
                It.Is<Notification>(n =>
                    n.TargetId       == "user-1" &&
                    n.TargetType     == "user"   &&
                    n.Message        == "Hello"  &&
                    n.RecipientCount == 1),
                It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task SendToUser_UserNotConnected_Returns404WithoutSending()
    {
        _connectionManager
            .Setup(m => m.GetConnections("user-1"))
            .Returns(Array.Empty<string>());

        var result = await _controller.SendToUser("user-1", new SendNotificationDto("Hello"));

        Assert.IsType<NotFoundObjectResult>(result);
        _singleClientProxy.Verify(
            p => p.SendCoreAsync(It.IsAny<string>(), It.IsAny<object[]>(), It.IsAny<CancellationToken>()),
            Times.Never);
        _notificationStore.Verify(
            s => s.SaveAsync(It.IsAny<Notification>(), It.IsAny<CancellationToken>()),
            Times.Never);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public async Task SendToUser_BlankUserId_Returns400(string userId)
    {
        var result = await _controller.SendToUser(userId, new SendNotificationDto("Hello"));

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task SendToUser_PayloadContainsCorrectEventMethod()
    {
        _connectionManager
            .Setup(m => m.GetConnections("user-1"))
            .Returns(new[] { "conn-a" });

        await _controller.SendToUser("user-1", new SendNotificationDto("Test"));

        // The method name sent to clients must match the client-side listener
        _singleClientProxy.Verify(
            p => p.SendCoreAsync(
                "ReceiveNotification",
                It.Is<object[]>(args => args.Length == 1),
                It.IsAny<CancellationToken>()),
            Times.Once);
    }

    // ── SendToGroup ────────────────────────────────────────────────────────────

    [Fact]
    public async Task SendToGroup_ValidTag_SendsToGroupAndReturns200()
    {
        var result = await _controller.SendToGroup("premium", new SendNotificationDto("Deal!"));

        var ok = Assert.IsType<OkObjectResult>(result);
        _hubClients.Verify(c => c.Group("premium"), Times.Once);
        _groupProxy.Verify(
            p => p.SendCoreAsync("ReceiveNotification", It.IsAny<object[]>(), It.IsAny<CancellationToken>()),
            Times.Once);
        var json = JsonSerializer.Serialize(ok.Value);
        var doc = JsonDocument.Parse(json);
        Assert.Equal("premium", doc.RootElement.GetProperty("group").GetString());
    }

    [Fact]
    public async Task SendToGroup_ValidTag_SavesNotificationToStore()
    {
        await _controller.SendToGroup("premium", new SendNotificationDto("Deal!"));

        _notificationStore.Verify(
            s => s.SaveAsync(
                It.Is<Notification>(n =>
                    n.TargetId       == "premium" &&
                    n.TargetType     == "group"   &&
                    n.Message        == "Deal!"   &&
                    n.RecipientCount == 0),
                It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public async Task SendToGroup_BlankTag_Returns400(string tag)
    {
        var result = await _controller.SendToGroup(tag, new SendNotificationDto("Hello"));

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task SendToGroup_DoesNotQueryConnectionManager()
    {
        await _controller.SendToGroup("some-group", new SendNotificationDto("msg"));

        // Group broadcast goes straight to SignalR — connection manager is not involved
        _connectionManager.Verify(m => m.GetConnections(It.IsAny<string>()), Times.Never);
        _connectionManager.Verify(m => m.HasConnections(It.IsAny<string>()), Times.Never);
    }

    // ── GetUserConnectionStatus ────────────────────────────────────────────────

    [Fact]
    public void GetUserConnectionStatus_ConnectedUser_ReturnsIsConnectedTrue()
    {
        _connectionManager.Setup(m => m.HasConnections("user-1")).Returns(true);
        _connectionManager.Setup(m => m.GetConnections("user-1")).Returns(new[] { "conn-a" });

        var result = _controller.GetUserConnectionStatus("user-1");

        var ok = Assert.IsType<OkObjectResult>(result);
        var json = JsonSerializer.Serialize(ok.Value);
        var doc = JsonDocument.Parse(json);
        Assert.True(doc.RootElement.GetProperty("isConnected").GetBoolean());
        Assert.Equal(1, doc.RootElement.GetProperty("connectionCount").GetInt32());
    }

    [Fact]
    public void GetUserConnectionStatus_NotConnectedUser_ReturnsIsConnectedFalse()
    {
        _connectionManager.Setup(m => m.HasConnections("user-1")).Returns(false);
        _connectionManager.Setup(m => m.GetConnections("user-1")).Returns(Array.Empty<string>());

        var result = _controller.GetUserConnectionStatus("user-1");

        var ok = Assert.IsType<OkObjectResult>(result);
        var json = JsonSerializer.Serialize(ok.Value);
        var doc = JsonDocument.Parse(json);
        Assert.False(doc.RootElement.GetProperty("isConnected").GetBoolean());
        Assert.Equal(0, doc.RootElement.GetProperty("connectionCount").GetInt32());
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public void GetUserConnectionStatus_BlankUserId_Returns400(string userId)
    {
        var result = _controller.GetUserConnectionStatus(userId);

        Assert.IsType<BadRequestObjectResult>(result);
    }
}
