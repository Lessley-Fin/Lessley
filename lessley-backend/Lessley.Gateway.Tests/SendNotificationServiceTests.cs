using Lessley.Gateway.Api.Hubs;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Classes;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.SignalR;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Xunit;

namespace Lessley.Gateway.Tests;

public class SendNotificationServiceTests
{
    private readonly Mock<IConnectionManager> _connectionManager = new();
    private readonly Mock<INotificationRepository> _notificationRepository = new();
    private readonly Mock<UserManager<ApplicationUser>> _userManager;
    private readonly Mock<ISingleClientProxy> _singleClientProxy = new();
    private readonly Mock<IClientProxy> _groupProxy = new();
    private readonly Mock<IHubClients> _hubClients = new();
    private readonly Mock<IHubContext<NotificationHub>> _hubContext = new();
    private readonly SendNotificationService _service;

    public SendNotificationServiceTests()
    {
        _singleClientProxy
            .Setup(p => p.SendCoreAsync(It.IsAny<string>(), It.IsAny<object[]>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        _groupProxy
            .Setup(p => p.SendCoreAsync(It.IsAny<string>(), It.IsAny<object[]>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        _hubClients.Setup(c => c.Client(It.IsAny<string>())).Returns(_singleClientProxy.Object);
        _hubClients.Setup(c => c.Group(It.IsAny<string>())).Returns(_groupProxy.Object);
        _hubContext.Setup(h => h.Clients).Returns(_hubClients.Object);

        _notificationRepository
            .Setup(s => s.SaveAsync(It.IsAny<Notification>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        _notificationRepository
            .Setup(s => s.SaveManyAsync(It.IsAny<IEnumerable<Notification>>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var store = new Mock<IUserStore<ApplicationUser>>();
        _userManager = new Mock<UserManager<ApplicationUser>>(
            store.Object, null!, null!, null!, null!, null!, null!, null!, null!);

        _userManager.Setup(m => m.Users)
            .Returns(Array.Empty<ApplicationUser>().AsAsyncQueryable());

        var bus = new NoOpPublishEndpoint();
        var httpContextAccessor = new Mock<IHttpContextAccessor>();
        httpContextAccessor.Setup(a => a.HttpContext).Returns((HttpContext?)null);

        _service = new SendNotificationService(
            _hubContext.Object,
            _connectionManager.Object,
            _notificationRepository.Object,
            _userManager.Object,
            bus,
            httpContextAccessor.Object,
            NullLogger<SendNotificationService>.Instance);
    }

    // ── SendToUserAsync ────────────────────────────────────────────────────────

    [Fact]
    public async Task SendToUser_WithConnections_SendsToEachAndReturnsCount()
    {
        _connectionManager
            .Setup(m => m.GetConnections("user-1"))
            .Returns(new[] { "conn-a", "conn-b" });

        var count = await _service.SendToUserAsync("user-1", "Hello");

        Assert.Equal(2, count);
        _hubClients.Verify(c => c.Client(It.IsAny<string>()), Times.Exactly(2));
        _singleClientProxy.Verify(
            p => p.SendCoreAsync("DealUserNotification", It.IsAny<object[]>(), It.IsAny<CancellationToken>()),
            Times.Exactly(2));
    }

    [Fact]
    public async Task SendToUser_WithConnections_SavesNotificationToRepository()
    {
        _connectionManager
            .Setup(m => m.GetConnections("user-1"))
            .Returns(new[] { "conn-a" });

        await _service.SendToUserAsync("user-1", "Hello", "deal-123");

        _notificationRepository.Verify(
            s => s.SaveAsync(
                It.Is<Notification>(n =>
                    n.UserId == "user-1" &&
                    n.Type   == "user"   &&
                    n.Message == "Hello" &&
                    n.DealId  == "deal-123"),
                It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task SendToUser_NoConnections_PersistsButDoesNotPushAndReturnsZero()
    {
        _connectionManager
            .Setup(m => m.GetConnections("user-1"))
            .Returns(Array.Empty<string>());

        var count = await _service.SendToUserAsync("user-1", "Hello");

        Assert.Equal(0, count);
        _singleClientProxy.Verify(
            p => p.SendCoreAsync(It.IsAny<string>(), It.IsAny<object[]>(), It.IsAny<CancellationToken>()),
            Times.Never);
        _notificationRepository.Verify(
            s => s.SaveAsync(
                It.Is<Notification>(n => n.UserId == "user-1" && n.Type == "user" && n.Message == "Hello"),
                It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task SendToUser_UsesCorrectEventName_DealUserNotification()
    {
        _connectionManager
            .Setup(m => m.GetConnections("user-1"))
            .Returns(new[] { "conn-a" });

        await _service.SendToUserAsync("user-1", "Test");

        _singleClientProxy.Verify(
            p => p.SendCoreAsync(
                "DealUserNotification",
                It.Is<object[]>(args => args.Length == 1),
                It.IsAny<CancellationToken>()),
            Times.Once);
    }

    // ── SendToGroupAsync ───────────────────────────────────────────────────────

    [Fact]
    public async Task SendToGroup_SendsToGroupAndSavesToRepository()
    {
        await _service.SendToGroupAsync("premium", "Deal!", "deal-456");

        _hubClients.Verify(c => c.Group("premium"), Times.Once);
        _groupProxy.Verify(
            p => p.SendCoreAsync("DealGroupNotification", It.IsAny<object[]>(), It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task SendToGroup_UsesCorrectEventName_DealGroupNotification()
    {
        await _service.SendToGroupAsync("tech", "New deal!");

        _groupProxy.Verify(
            p => p.SendCoreAsync("DealGroupNotification", It.IsAny<object[]>(), It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task SendToGroup_WithMatchingUsers_PersistsNotificationsForEach()
    {
        var userId = "user-abc";
        _userManager.Setup(m => m.Users)
            .Returns(new[] { new ApplicationUser { Id = userId, Email = "user-abc@test.com", Tags = new List<string> { "tech" } } }
                .AsAsyncQueryable());

        await _service.SendToGroupAsync("tech", "New deal!");

        _notificationRepository.Verify(
            s => s.SaveManyAsync(
                It.Is<IEnumerable<Notification>>(ns =>
                    ns.Any(n => n.UserId == "user-abc@test.com" && n.Type == "group")),
                It.IsAny<CancellationToken>()),
            Times.Once);
    }
}
