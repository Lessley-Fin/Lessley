using System.Text.Json;
using Lessley.Gateway.Api.Controllers;
using Xunit;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;

namespace Lessley.Gateway.Tests;

public class NotificationControllerTests
{
    private readonly Mock<IConnectionManager> _connectionManager = new();
    private readonly Mock<ISendNotificationService> _sendNotificationService = new();
    private readonly Mock<INotificationService> _notificationService = new();
    private readonly Mock<UserManager<ApplicationUser>> _userManager;
    private readonly NotificationController _controller;

    public NotificationControllerTests()
    {
        var store = new Mock<IUserStore<ApplicationUser>>();
        _userManager = new Mock<UserManager<ApplicationUser>>(
            store.Object, null!, null!, null!, null!, null!, null!, null!, null!);

        // The controller addresses users by email but keys internal state on user.Id.
        // Resolve any email to a user whose Id equals that email, so existing assertions
        // (which pass the same string as both the route value and the expected id) hold.
        _userManager
            .Setup(m => m.FindByEmailAsync(It.IsAny<string>()))
            .ReturnsAsync((string email) => new ApplicationUser { Id = email, Email = email });

        _controller = new NotificationController(
            _connectionManager.Object,
            _sendNotificationService.Object,
            _notificationService.Object,
            _userManager.Object,
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
    public async Task SendToUser_UserOffline_StillPersistsViaServiceAndReturns200()
    {
        // Offline (0 live connections) — the service still persists, so delivery succeeds.
        _sendNotificationService
            .Setup(s => s.SendToUserAsync("user-1", "Hello", null, It.IsAny<CancellationToken>()))
            .ReturnsAsync(0);

        var result = await _controller.SendToUser("user-1", new SendNotificationDto("Hello"));

        var ok  = Assert.IsType<OkObjectResult>(result);
        var doc = JsonDocument.Parse(JsonSerializer.Serialize(ok.Value));
        Assert.Equal(0, doc.RootElement.GetProperty("recipientCount").GetInt32());
        _sendNotificationService.Verify(
            s => s.SendToUserAsync("user-1", "Hello", null, It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task SendToUser_UnknownUser_Returns404()
    {
        _userManager.Setup(m => m.FindByEmailAsync("ghost")).ReturnsAsync((ApplicationUser?)null);

        var result = await _controller.SendToUser("ghost", new SendNotificationDto("Hello"));

        Assert.IsType<NotFoundObjectResult>(result);
        _sendNotificationService.Verify(
            s => s.SendToUserAsync(It.IsAny<string>(), It.IsAny<string>(), It.IsAny<string?>(), It.IsAny<CancellationToken>()),
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
    public async Task GetUserConnectionStatus_ConnectedUser_ReturnsIsConnectedTrue()
    {
        _connectionManager.Setup(m => m.HasConnections("user-1")).Returns(true);
        _connectionManager.Setup(m => m.GetConnections("user-1")).Returns(new[] { "conn-a" });

        var result = await _controller.GetUserConnectionStatus("user-1");

        var ok  = Assert.IsType<OkObjectResult>(result);
        var doc = JsonDocument.Parse(JsonSerializer.Serialize(ok.Value));
        Assert.True(doc.RootElement.GetProperty("isConnected").GetBoolean());
        Assert.Equal(1, doc.RootElement.GetProperty("connectionCount").GetInt32());
    }

    [Fact]
    public async Task GetUserConnectionStatus_NotConnectedUser_ReturnsIsConnectedFalse()
    {
        _connectionManager.Setup(m => m.HasConnections("user-1")).Returns(false);
        _connectionManager.Setup(m => m.GetConnections("user-1")).Returns(Array.Empty<string>());

        var result = await _controller.GetUserConnectionStatus("user-1");

        var ok  = Assert.IsType<OkObjectResult>(result);
        var doc = JsonDocument.Parse(JsonSerializer.Serialize(ok.Value));
        Assert.False(doc.RootElement.GetProperty("isConnected").GetBoolean());
        Assert.Equal(0, doc.RootElement.GetProperty("connectionCount").GetInt32());
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public async Task GetUserConnectionStatus_BlankUserId_Returns400(string email)
    {
        var result = await _controller.GetUserConnectionStatus(email);

        Assert.IsType<BadRequestObjectResult>(result);
    }

    // ── GetUserNotifications ───────────────────────────────────────────────────

    [Fact]
    public async Task GetUserNotifications_ReturnsListFromService()
    {
        var notifications = new List<NotificationDto>
        {
            new() { Message = "Hello", TargetType = "user", IsRead = false },
            new() { Message = "World", TargetType = "user", IsRead = true },
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
            .ReturnsAsync(new List<NotificationDto>());

        var result = await _controller.GetUserNotifications("user-2", CancellationToken.None);

        var ok   = Assert.IsType<OkObjectResult>(result);
        var list = Assert.IsAssignableFrom<List<NotificationDto>>(ok.Value);
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

    // ── MarkAllAsRead ──────────────────────────────────────────────────────────

    [Fact]
    public async Task MarkAllAsRead_CallsServiceAndReturns200()
    {
        _notificationService
            .Setup(s => s.MarkAllAsReadAsync("user-1", It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var result = await _controller.MarkAllAsRead("user-1", CancellationToken.None);

        Assert.IsType<OkObjectResult>(result);
        _notificationService.Verify(
            s => s.MarkAllAsReadAsync("user-1", It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public async Task MarkAllAsRead_BlankUserId_Returns400(string userId)
    {
        var result = await _controller.MarkAllAsRead(userId, CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result);
    }
}
