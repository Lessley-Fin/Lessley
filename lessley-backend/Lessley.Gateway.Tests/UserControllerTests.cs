using System.Security.Claims;
using Lessley.Gateway.Api.Controllers;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Xunit;

namespace Lessley.Gateway.Tests;

public class UserControllerTests
{
    private readonly Mock<UserManager<ApplicationUser>> _userManager;
    private readonly Mock<IUserTagService> _userTagService = new();
    private readonly Mock<IPersonalizationService> _personalizationService = new();
    private readonly UserController _controller;

    public UserControllerTests()
    {
        var store = new Mock<IUserStore<ApplicationUser>>();
        _userManager = new Mock<UserManager<ApplicationUser>>(
            store.Object, null!, null!, null!, null!, null!, null!, null!, null!);

        _controller = new UserController(
            _userManager.Object,
            _userTagService.Object,
            _personalizationService.Object,
            NullLogger<UserController>.Instance);
        SetCallerContext("admin@test.com", "Admin");
    }

    // Callers are identified by their email claim (NameIdentifier still carries user.Id,
    // but the controller authorizes self-updates by comparing the email claim to the route).
    private void SetCallerContext(string callerEmail, string role)
    {
        var identity = new ClaimsIdentity(new[]
        {
            new Claim(ClaimTypes.NameIdentifier, "caller-id"),
            new Claim(ClaimTypes.Email, callerEmail),
            new Claim(ClaimTypes.Role, role),
        }, "Bearer");
        _controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext { User = new ClaimsPrincipal(identity) }
        };
    }

    // ── UpdateUser ─────────────────────────────────────────────────────────────

    [Fact]
    public async Task UpdateUser_UserNotFound_Returns404()
    {
        _userManager.Setup(m => m.FindByEmailAsync("ghost")).ReturnsAsync((ApplicationUser?)null);

        var result = await _controller.UpdateUser("ghost", new UpdateUserDto(null, null, null));

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task UpdateUser_UpdatesMutedTagsClubsAndScore()
    {
        var user = new ApplicationUser
        {
            Id            = "user-1",
            Tags          = new List<string> { "tech" },
            MutedTags     = new List<string>(),
            Clubs         = new List<string>(),
            MatchingScore = null
        };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Success);

        var dto    = new UpdateUserDto(new List<string> { "sports" }, new List<string> { "club-a" }, 0.75);
        var result = await _controller.UpdateUser("user-1", dto);

        Assert.IsType<OkObjectResult>(result);
        _userManager.Verify(m => m.UpdateAsync(It.Is<ApplicationUser>(u =>
            u.MutedTags!.Contains("sports") &&
            u.Clubs!.Contains("club-a") &&
            u.MatchingScore == 0.75)), Times.Once);
    }

    [Fact]
    public async Task UpdateUser_IdentityFailure_Returns400()
    {
        var user = new ApplicationUser { Id = "user-1" };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Failed(new IdentityError { Description = "Update failed" }));

        var result = await _controller.UpdateUser("user-1", new UpdateUserDto(null, null, null));

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task UpdateUser_NullDto_PersistsWithNoChanges()
    {
        var user = new ApplicationUser
        {
            Id            = "user-1",
            Tags          = new List<string> { "tech" },
            MutedTags     = new List<string> { "ads" },
            Clubs         = new List<string> { "club-1" },
            MatchingScore = 0.5
        };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Success);

        var result = await _controller.UpdateUser("user-1", new UpdateUserDto(null, null, null));

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public async Task UpdateUser_MatchingScoreChanged_TriggersRecalculation()
    {
        var user = new ApplicationUser { Id = "user-1", Email = "user-1", MatchingScore = 0.25, MutedTags = new() };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>())).ReturnsAsync(IdentityResult.Success);

        var result = await _controller.UpdateUser("user-1", new UpdateUserDto(null, null, 0.75));

        Assert.IsType<OkObjectResult>(result);
        _personalizationService.Verify(
            s => s.RecalculateCategoriesAsync("user-1", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task UpdateUser_MutedCategoriesChanged_SyncsGroupsAndTriggersRecalculation()
    {
        var user = new ApplicationUser { Id = "user-1", Email = "user-1", MutedTags = new List<string> { "5411" } };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>())).ReturnsAsync(IdentityResult.Success);

        var result = await _controller.UpdateUser("user-1", new UpdateUserDto(new List<string> { "5812" }, null, null));

        Assert.IsType<OkObjectResult>(result);
        // Muted-tag change must immediately re-sync SignalR groups
        _userTagService.Verify(
            s => s.SyncGroupsAsync("user-1", It.IsAny<IReadOnlyList<string>>(), It.IsAny<CancellationToken>()), Times.Once);
        // And must trigger Personalization recalculation
        _personalizationService.Verify(
            s => s.RecalculateCategoriesAsync("user-1", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task UpdateUser_OnlyClubsChanged_DoesNotTriggerRecalculation()
    {
        var user = new ApplicationUser { Id = "user-1", Email = "user-1", MatchingScore = 0.5, MutedTags = new List<string> { "5411" } };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>())).ReturnsAsync(IdentityResult.Success);

        var result = await _controller.UpdateUser("user-1", new UpdateUserDto(null, new List<string> { "club-a" }, null));

        Assert.IsType<OkObjectResult>(result);
        _personalizationService.Verify(
            s => s.RecalculateCategoriesAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()), Times.Never);
    }

    [Fact]
    public async Task RecalculateCategories_ValidUser_TriggersServiceAndReturns202()
    {
        var user = new ApplicationUser { Id = "user-1", Email = "user-1" };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);

        var result = await _controller.RecalculateCategories("user-1");

        Assert.IsType<AcceptedResult>(result);
        _personalizationService.Verify(
            s => s.RecalculateCategoriesAsync("user-1", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task RecalculateCategories_UnknownUser_Returns404()
    {
        _userManager.Setup(m => m.FindByEmailAsync("ghost")).ReturnsAsync((ApplicationUser?)null);

        var result = await _controller.RecalculateCategories("ghost");

        Assert.IsType<NotFoundObjectResult>(result);
        _personalizationService.Verify(
            s => s.RecalculateCategoriesAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()), Times.Never);
    }

    // ── UpdateUser: auth check ─────────────────────────────────────────────────

    [Fact]
    public async Task UpdateUser_NonAdminUpdatingOwnProfile_Returns200()
    {
        SetCallerContext("user-1", "Viewer");

        var user = new ApplicationUser { Id = "user-1" };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Success);

        var result = await _controller.UpdateUser("user-1", new UpdateUserDto(null, null, null));

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public async Task UpdateUser_NonAdminUpdatingOtherUser_ReturnsForbid()
    {
        SetCallerContext("viewer-id", "Viewer");

        var result = await _controller.UpdateUser("different-user", new UpdateUserDto(null, null, null));

        Assert.IsType<ForbidResult>(result);
        _userManager.Verify(m => m.FindByEmailAsync(It.IsAny<string>()), Times.Never);
    }

    // ── UpdateUserTags ─────────────────────────────────────────────────────────

    [Fact]
    public async Task UpdateUserTags_UserNotFound_Returns404()
    {
        _userManager.Setup(m => m.FindByEmailAsync("ghost")).ReturnsAsync((ApplicationUser?)null);

        var result = await _controller.UpdateUserTags("ghost", new[] { "tech" });

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task UpdateUserTags_ValidRequest_CallsUserTagServiceAndReturns200()
    {
        var user = new ApplicationUser { Id = "user-1" };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userTagService
            .Setup(s => s.AssignTagsAsync("user-1", It.IsAny<string[]>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var result = await _controller.UpdateUserTags("user-1", new[] { "food", "travel" });

        Assert.IsType<OkObjectResult>(result);
        _userTagService.Verify(s => s.AssignTagsAsync(
            "user-1",
            It.Is<string[]>(t => t.Contains("food") && t.Contains("travel")),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task UpdateUserTags_EmptyArray_StillCallsUserTagService()
    {
        var user = new ApplicationUser { Id = "user-1" };
        _userManager.Setup(m => m.FindByEmailAsync("user-1")).ReturnsAsync(user);
        _userTagService
            .Setup(s => s.AssignTagsAsync("user-1", It.IsAny<string[]>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var result = await _controller.UpdateUserTags("user-1", Array.Empty<string>());

        Assert.IsType<OkObjectResult>(result);
        _userTagService.Verify(s => s.AssignTagsAsync(
            "user-1",
            It.Is<string[]>(t => t.Length == 0),
            It.IsAny<CancellationToken>()), Times.Once);
    }
}
