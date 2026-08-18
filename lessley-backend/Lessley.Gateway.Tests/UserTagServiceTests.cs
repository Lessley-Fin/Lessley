using Lessley.Gateway.Api.Hubs;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Classes;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.SignalR;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Xunit;

namespace Lessley.Gateway.Tests;

public class UserTagServiceTests
{
    private readonly Mock<UserManager<ApplicationUser>> _userManager;
    private readonly Mock<IConnectionManager> _connectionManager = new();
    private readonly Mock<IHubContext<NotificationHub>> _hubContext = new();
    private readonly Mock<IGroupManager> _groupManager = new();
    private readonly Mock<IHubClients> _clients = new();
    private readonly Mock<ISingleClientProxy> _clientProxy = new();
    private readonly UserTagService _service;

    public UserTagServiceTests()
    {
        var store = new Mock<IUserStore<ApplicationUser>>();
        _userManager = new Mock<UserManager<ApplicationUser>>(
            store.Object, null!, null!, null!, null!, null!, null!, null!, null!);

        _hubContext.Setup(h => h.Groups).Returns(_groupManager.Object);

        // Assigning tags also pushes CategoriesUpdated to the user's open tabs.
        _hubContext.Setup(h => h.Clients).Returns(_clients.Object);
        _clients.Setup(c => c.Client(It.IsAny<string>())).Returns(_clientProxy.Object);
        _clientProxy
            .Setup(p => p.SendCoreAsync(It.IsAny<string>(), It.IsAny<object?[]>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        _groupManager
            .Setup(g => g.AddToGroupAsync(It.IsAny<string>(), It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        _groupManager
            .Setup(g => g.RemoveFromGroupAsync(It.IsAny<string>(), It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        _service = new UserTagService(
            _userManager.Object,
            _connectionManager.Object,
            _hubContext.Object,
            NullLogger<UserTagService>.Instance);
    }

    [Fact]
    public async Task AssignTags_UserNotFound_DoesNotUpdateOrAddGroups()
    {
        _userManager.Setup(m => m.FindByEmailAsync("ghost")).ReturnsAsync((ApplicationUser?)null);

        await _service.AssignTagsAsync("ghost", new[] { "tech" });

        _userManager.Verify(m => m.UpdateAsync(It.IsAny<ApplicationUser>()), Times.Never);
        _groupManager.Verify(g => g.AddToGroupAsync(It.IsAny<string>(), It.IsAny<string>(), It.IsAny<CancellationToken>()), Times.Never);
    }

    [Fact]
    public async Task AssignTags_UserOffline_PersistsTagsWithoutSignalR()
    {
        var user = new ApplicationUser { Id = "user-1", Tags = new List<string>() };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Success);
        _connectionManager.Setup(m => m.GetConnections("user-1")).Returns(Array.Empty<string>());

        await _service.AssignTagsAsync("user-1", new[] { "tech", "sports" });

        _userManager.Verify(m => m.UpdateAsync(It.Is<ApplicationUser>(u =>
            u.Tags!.Contains("tech") && u.Tags.Contains("sports"))), Times.Once);
        _groupManager.Verify(g => g.AddToGroupAsync(It.IsAny<string>(), It.IsAny<string>(), It.IsAny<CancellationToken>()), Times.Never);
    }

    [Fact]
    public async Task AssignTags_UserOnline_RemovesOldGroupsAndAddsNewOnes()
    {
        var user = new ApplicationUser
        {
            Id       = "user-1",
            Tags     = new List<string> { "old-tag" },
            MutedTags = new List<string>()
        };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Success);
        _connectionManager.Setup(m => m.GetConnections("user-1"))
            .Returns(new[] { "conn-1" });

        await _service.AssignTagsAsync("user-1", new[] { "new-tag" });

        _groupManager.Verify(g => g.RemoveFromGroupAsync("conn-1", "old-tag", It.IsAny<CancellationToken>()), Times.Once);
        _groupManager.Verify(g => g.AddToGroupAsync("conn-1", "new-tag", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task AssignTags_MutedTagsNotAddedToGroups()
    {
        var user = new ApplicationUser
        {
            Id        = "user-1",
            Tags      = new List<string>(),
            MutedTags = new List<string> { "muted-tag" }
        };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Success);
        _connectionManager.Setup(m => m.GetConnections("user-1"))
            .Returns(new[] { "conn-1" });

        await _service.AssignTagsAsync("user-1", new[] { "active-tag", "muted-tag" });

        _groupManager.Verify(g => g.AddToGroupAsync("conn-1", "active-tag", It.IsAny<CancellationToken>()), Times.Once);
        _groupManager.Verify(g => g.AddToGroupAsync("conn-1", "muted-tag", It.IsAny<CancellationToken>()), Times.Never);
    }

    [Fact]
    public async Task AssignTags_MultipleConnections_UpdatesAllConnections()
    {
        var user = new ApplicationUser
        {
            Id       = "user-1",
            Tags     = new List<string>(),
            MutedTags = new List<string>()
        };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Success);
        _connectionManager.Setup(m => m.GetConnections("user-1"))
            .Returns(new[] { "conn-1", "conn-2" });

        await _service.AssignTagsAsync("user-1", new[] { "tag-a" });

        _groupManager.Verify(g => g.AddToGroupAsync("conn-1", "tag-a", It.IsAny<CancellationToken>()), Times.Once);
        _groupManager.Verify(g => g.AddToGroupAsync("conn-2", "tag-a", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task AssignTags_EmptyTagArray_ClearsAllGroups()
    {
        var user = new ApplicationUser
        {
            Id       = "user-1",
            Tags     = new List<string> { "tech", "sports" },
            MutedTags = new List<string>()
        };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Success);
        _connectionManager.Setup(m => m.GetConnections("user-1"))
            .Returns(new[] { "conn-1" });

        await _service.AssignTagsAsync("user-1", Array.Empty<string>());

        _groupManager.Verify(g => g.RemoveFromGroupAsync("conn-1", "tech",   It.IsAny<CancellationToken>()), Times.Once);
        _groupManager.Verify(g => g.RemoveFromGroupAsync("conn-1", "sports", It.IsAny<CancellationToken>()), Times.Once);
        _groupManager.Verify(g => g.AddToGroupAsync(It.IsAny<string>(), It.IsAny<string>(), It.IsAny<CancellationToken>()), Times.Never);
    }

    // ── telling the client its cached categories are stale ────────────────────

    [Fact]
    public async Task AssignTags_UserOnline_PushesCategoriesUpdatedToEveryConnection()
    {
        var user = new ApplicationUser { Id = "user-1", Tags = new List<string>(), MutedTags = new List<string>() };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>())).ReturnsAsync(IdentityResult.Success);
        _connectionManager.Setup(m => m.GetConnections("user-1")).Returns(new[] { "conn-1", "conn-2" });

        await _service.AssignTagsAsync("user-1", new[] { "tag-a" });

        // The event name is a contract with the client's useSignalR handler.
        _clients.Verify(c => c.Client("conn-1"), Times.AtLeastOnce);
        _clients.Verify(c => c.Client("conn-2"), Times.AtLeastOnce);
        _clientProxy.Verify(p => p.SendCoreAsync(
            "CategoriesUpdated", It.IsAny<object?[]>(), It.IsAny<CancellationToken>()), Times.Exactly(2));
    }

    [Fact]
    public async Task AssignTags_UserOffline_SendsNothing()
    {
        // Normal, not exceptional: the sweep runs at midnight and the bank journey navigates
        // the browser away. Those clients refresh on reconnect instead.
        var user = new ApplicationUser { Id = "user-1", Tags = new List<string>(), MutedTags = new List<string>() };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>())).ReturnsAsync(IdentityResult.Success);
        _connectionManager.Setup(m => m.GetConnections("user-1")).Returns(Array.Empty<string>());

        await _service.AssignTagsAsync("user-1", new[] { "tag-a" });

        _clientProxy.Verify(p => p.SendCoreAsync(
            It.IsAny<string>(), It.IsAny<object?[]>(), It.IsAny<CancellationToken>()), Times.Never);
    }

    [Fact]
    public async Task AssignTags_FailedWrite_SendsNoUpdate()
    {
        // Nothing changed, so there is nothing for the client to re-fetch — and the throw
        // gets the message redelivered.
        var user = new ApplicationUser { Id = "user-1", Tags = new List<string>(), MutedTags = new List<string>() };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Failed(new IdentityError { Description = "concurrency" }));
        _connectionManager.Setup(m => m.GetConnections("user-1")).Returns(new[] { "conn-1" });

        await Assert.ThrowsAsync<InvalidOperationException>(
            () => _service.AssignTagsAsync("user-1", new[] { "tag-a" }));

        _clientProxy.Verify(p => p.SendCoreAsync(
            It.IsAny<string>(), It.IsAny<object?[]>(), It.IsAny<CancellationToken>()), Times.Never);
    }
}
