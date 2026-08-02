using System.Security.Claims;
using System.Text.Json;
using Lessley.Gateway.Api.Controllers;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using MongoDB.Bson;
using Moq;
using Xunit;

namespace Lessley.Gateway.Tests;

public class NotificationControllerTests
{
    private readonly Mock<IConnectionManager> _connectionManager = new();
    private readonly Mock<INotificationService> _notificationService = new();
    private readonly NotificationController _controller;

    public NotificationControllerTests()
    {
        _controller = new NotificationController(
            _connectionManager.Object,
            _notificationService.Object,
            NullLogger<NotificationController>.Instance);

        SetCaller("user-1@test.com");
    }

    private void SetCaller(string email)
    {
        var identity = new ClaimsIdentity(new[]
        {
            new Claim(ClaimTypes.Email, email),
            new Claim(ClaimTypes.NameIdentifier, "id-" + email),
        }, "Bearer");
        _controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext { User = new ClaimsPrincipal(identity) }
        };
    }

    // ── GetUserNotifications ───────────────────────────────────────────────────

    [Fact]
    public async Task GetUserNotifications_ReturnsListFromService()
    {
        var notifications = new List<NotificationDto>
        {
            new() { Message = "Hello", Type = "user", IsRead = false },
            new() { Message = "World", Type = "user", IsRead = true },
        };
        _notificationService
            .Setup(s => s.GetUserNotificationsAsync("user-1@test.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync(notifications);

        var result = await _controller.GetUserNotifications(CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        Assert.Equal(notifications, ok.Value);
    }

    [Fact]
    public async Task GetUserNotifications_EmptyResult_ReturnsEmptyList()
    {
        _notificationService
            .Setup(s => s.GetUserNotificationsAsync("user-1@test.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync(new List<NotificationDto>());

        var result = await _controller.GetUserNotifications(CancellationToken.None);

        var ok   = Assert.IsType<OkObjectResult>(result);
        var list = Assert.IsAssignableFrom<List<NotificationDto>>(ok.Value);
        Assert.Empty(list);
    }

    // ── GetUserConnectionStatus ────────────────────────────────────────────────

    [Fact]
    public void GetUserConnectionStatus_ConnectedUser_ReturnsIsConnectedTrue()
    {
        _connectionManager.Setup(m => m.HasConnections("user-1@test.com")).Returns(true);
        _connectionManager.Setup(m => m.GetConnections("user-1@test.com")).Returns(new[] { "conn-a" });

        var result = _controller.GetUserConnectionStatus();

        var ok  = Assert.IsType<OkObjectResult>(result);
        var doc = JsonDocument.Parse(JsonSerializer.Serialize(ok.Value));
        Assert.True(doc.RootElement.GetProperty("isConnected").GetBoolean());
        Assert.Equal(1, doc.RootElement.GetProperty("connectionCount").GetInt32());
    }

    [Fact]
    public void GetUserConnectionStatus_NotConnectedUser_ReturnsIsConnectedFalse()
    {
        _connectionManager.Setup(m => m.HasConnections("user-1@test.com")).Returns(false);
        _connectionManager.Setup(m => m.GetConnections("user-1@test.com")).Returns(Array.Empty<string>());

        var result = _controller.GetUserConnectionStatus();

        var ok  = Assert.IsType<OkObjectResult>(result);
        var doc = JsonDocument.Parse(JsonSerializer.Serialize(ok.Value));
        Assert.False(doc.RootElement.GetProperty("isConnected").GetBoolean());
        Assert.Equal(0, doc.RootElement.GetProperty("connectionCount").GetInt32());
    }

    // ── MarkAllAsRead ──────────────────────────────────────────────────────────

    [Fact]
    public async Task MarkAllAsRead_CallsServiceAndReturns200()
    {
        _notificationService
            .Setup(s => s.MarkAllAsReadAsync("user-1@test.com", It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var result = await _controller.MarkAllAsRead(CancellationToken.None);

        Assert.IsType<OkObjectResult>(result);
        _notificationService.Verify(
            s => s.MarkAllAsReadAsync("user-1@test.com", It.IsAny<CancellationToken>()),
            Times.Once);
    }

    // ── MarkAsRead (single) ────────────────────────────────────────────────────

    [Fact]
    public async Task MarkAsRead_ValidId_ReturnsOk()
    {
        var objectId = ObjectId.GenerateNewId();
        _notificationService
            .Setup(s => s.MarkAsReadAsync(objectId, "user-1@test.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync(true);

        var result = await _controller.MarkAsRead(objectId.ToString(), CancellationToken.None);

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public async Task MarkAsRead_NotFound_Returns404()
    {
        var objectId = ObjectId.GenerateNewId();
        _notificationService
            .Setup(s => s.MarkAsReadAsync(objectId, "user-1@test.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);

        var result = await _controller.MarkAsRead(objectId.ToString(), CancellationToken.None);

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task MarkAsRead_InvalidId_Returns400()
    {
        var result = await _controller.MarkAsRead("not-a-valid-objectid", CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result);
    }
}
