using System.Text.Json;
using Lessley.Gateway.Api.Controllers;
using Xunit;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;

namespace Lessley.Gateway.Tests;

public class NotificationControllerTests
{
    private readonly Mock<IConnectionManager> _connectionManager = new();
    private readonly Mock<ISendNotificationService> _sendNotificationService = new();
    private readonly Mock<INotificationService> _notificationService = new();
    private readonly NotificationController _controller;

    public NotificationControllerTests()
    {
        _controller = new NotificationController(
            _connectionManager.Object,
            _sendNotificationService.Object,
            _notificationService.Object,
            NullLogger<NotificationController>.Instance);
    }

    // ── SendToUser ─────────────────────────────────────────────────────────────

    [Fact]
    public async Task SendToUser_UserHasConnections_DelegatesToServiceAndReturns200()
    {
        _connectionManager.Setup(m => m.HasConnections("user-1")).Returns(true);
        _sendNotificationService
            .Setup(s => s.SendToUserAsync("user-1", "Hello", null, It.IsAny<CancellationToken>()))
            .ReturnsAsync(2);

        var result = await _controller.SendToUser("user-1", new SendNotificationDto("Hello"));

        var ok = Assert.IsType<OkObjectResult>(result);
        _sendNotificationService.Verify(
            s => s.SendToUserAsync("user-1", "Hello", null, It.IsAny<CancellationToken>()),
            Times.Once);
        var doc = JsonDocument.Parse(JsonSerializer.Serialize(ok.Value));
        Assert.Equal(2, doc.RootElement.GetProperty("recipientCount").GetInt32());
    }

    [Fact]
    public async Task SendToUser_UserNotConnected_Returns404WithoutCallingService()
    {
        _connectionManager.Setup(m => m.HasConnections("user-1")).Returns(false);

        var result = await _controller.SendToUser("user-1", new SendNotificationDto("Hello"));

        Assert.IsType<NotFoundObjectResult>(result);
        _sendNotificationService.Verify(
            s => s.SendToUserAsync(
                It.IsAny<string>(), It.IsAny<string>(),
                It.IsAny<string?>(), It.IsAny<CancellationToken>()),
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
    public async Task SendToUser_ServiceReturnsCount_CountReflectedInResponse()
    {
        _connectionManager.Setup(m => m.HasConnections("user-1")).Returns(true);
        _sendNotificationService
            .Setup(s => s.SendToUserAsync("user-1", "Test", null, It.IsAny<CancellationToken>()))
            .ReturnsAsync(3);

        var result = await _controller.SendToUser("user-1", new SendNotificationDto("Test"));

        var ok  = Assert.IsType<OkObjectResult>(result);
        var doc = JsonDocument.Parse(JsonSerializer.Serialize(ok.Value));
        Assert.Equal(3, doc.RootElement.GetProperty("recipientCount").GetInt32());
    }

    // ── SendToGroup ────────────────────────────────────────────────────────────

    [Fact]
    public async Task SendToGroup_ValidTag_DelegatesToServiceAndReturns200()
    {
        var result = await _controller.SendToGroup("premium", new SendNotificationDto("Deal!"));

        var ok = Assert.IsType<OkObjectResult>(result);
        _sendNotificationService.Verify(
            s => s.SendToGroupAsync("premium", "Deal!", null, It.IsAny<CancellationToken>()),
            Times.Once);
        var doc = JsonDocument.Parse(JsonSerializer.Serialize(ok.Value));
        Assert.Equal("premium", doc.RootElement.GetProperty("group").GetString());
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

        var ok  = Assert.IsType<OkObjectResult>(result);
        var doc = JsonDocument.Parse(JsonSerializer.Serialize(ok.Value));
        Assert.True(doc.RootElement.GetProperty("isConnected").GetBoolean());
        Assert.Equal(1, doc.RootElement.GetProperty("connectionCount").GetInt32());
    }

    [Fact]
    public void GetUserConnectionStatus_NotConnectedUser_ReturnsIsConnectedFalse()
    {
        _connectionManager.Setup(m => m.HasConnections("user-1")).Returns(false);
        _connectionManager.Setup(m => m.GetConnections("user-1")).Returns(Array.Empty<string>());

        var result = _controller.GetUserConnectionStatus("user-1");

        var ok  = Assert.IsType<OkObjectResult>(result);
        var doc = JsonDocument.Parse(JsonSerializer.Serialize(ok.Value));
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

    // ── GetUserNotifications ───────────────────────────────────────────────────

    [Fact]
    public async Task GetUserNotifications_ReturnsListFromService()
    {
        var notifications = new List<Notification>
        {
            new() { TargetId = "user-1", TargetType = "user", Message = "Hello", IsRead = false },
            new() { TargetId = "user-1", TargetType = "user", Message = "World", IsRead = true },
        };
        _notificationService
            .Setup(s => s.GetUserNotificationsAsync("user-1", It.IsAny<CancellationToken>()))
            .ReturnsAsync(notifications);

        var result = await _controller.GetUserNotifications("user-1", CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        Assert.Equal(notifications, ok.Value);
    }

    [Fact]
    public async Task GetUserNotifications_EmptyResult_ReturnsEmptyList()
    {
        _notificationService
            .Setup(s => s.GetUserNotificationsAsync("user-2", It.IsAny<CancellationToken>()))
            .ReturnsAsync(new List<Notification>());

        var result = await _controller.GetUserNotifications("user-2", CancellationToken.None);

        var ok   = Assert.IsType<OkObjectResult>(result);
        var list = Assert.IsAssignableFrom<List<Notification>>(ok.Value);
        Assert.Empty(list);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public async Task GetUserNotifications_BlankUserId_Returns400(string userId)
    {
        var result = await _controller.GetUserNotifications(userId, CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result);
    }

    // ── MarkUserNotificationsAsRead ────────────────────────────────────────────

    [Fact]
    public async Task MarkUserNotificationsAsRead_CallsServiceAndReturns200()
    {
        _notificationService
            .Setup(s => s.MarkUserNotificationsAsReadAsync("user-1", It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var result = await _controller.MarkUserNotificationsAsRead("user-1", CancellationToken.None);

        Assert.IsType<OkObjectResult>(result);
        _notificationService.Verify(
            s => s.MarkUserNotificationsAsReadAsync("user-1", It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public async Task MarkUserNotificationsAsRead_BlankUserId_Returns400(string userId)
    {
        var result = await _controller.MarkUserNotificationsAsRead(userId, CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result);
    }
}
