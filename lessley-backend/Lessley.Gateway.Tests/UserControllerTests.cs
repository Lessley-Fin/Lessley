using System.Text.Json;
using Lessley.Gateway.Api.Controllers;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Moq;
using Xunit;

namespace Lessley.Gateway.Tests;

public class UserControllerTests
{
    private readonly Mock<UserManager<ApplicationUser>> _userManager;
    private readonly Mock<IUserTagService> _userTagService = new();
    private readonly UserController _controller;

    public UserControllerTests()
    {
        var store = new Mock<IUserStore<ApplicationUser>>();
        _userManager = new Mock<UserManager<ApplicationUser>>(
            store.Object, null!, null!, null!, null!, null!, null!, null!, null!);

        _controller = new UserController(_userManager.Object, _userTagService.Object);
    }

    [Fact]
    public async Task UpdateUser_UserNotFound_Returns404()
    {
        _userManager.Setup(m => m.FindByIdAsync("ghost")).ReturnsAsync((ApplicationUser?)null);

        var result = await _controller.UpdateUser("ghost", new UpdateUserDto(null, null, null, null));

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
        _userManager.Setup(m => m.FindByIdAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Success);

        var dto    = new UpdateUserDto(null, new List<string> { "sports" }, new List<string> { "club-a" }, 0.75);
        var result = await _controller.UpdateUser("user-1", dto);

        var ok = Assert.IsType<OkObjectResult>(result);
        _userManager.Verify(m => m.UpdateAsync(It.Is<ApplicationUser>(u =>
            u.MutedTags!.Contains("sports") &&
            u.Clubs!.Contains("club-a") &&
            u.MatchingScore == 0.75)), Times.Once);
    }

    [Fact]
    public async Task UpdateUser_TagsChanged_CallsUserTagService()
    {
        var user = new ApplicationUser
        {
            Id    = "user-1",
            Tags  = new List<string> { "tech" }
        };
        _userManager.Setup(m => m.FindByIdAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Success);
        _userTagService
            .Setup(s => s.AssignTagsAsync("user-1", It.IsAny<string[]>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var dto = new UpdateUserDto(new List<string> { "food", "travel" }, null, null, null);
        await _controller.UpdateUser("user-1", dto);

        _userTagService.Verify(s => s.AssignTagsAsync(
            "user-1",
            It.Is<string[]>(t => t.Contains("food") && t.Contains("travel")),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task UpdateUser_TagsUnchanged_DoesNotCallUserTagService()
    {
        var user = new ApplicationUser
        {
            Id   = "user-1",
            Tags = new List<string> { "tech" }
        };
        _userManager.Setup(m => m.FindByIdAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Success);

        // Same tags as existing
        var dto = new UpdateUserDto(new List<string> { "tech" }, null, null, null);
        await _controller.UpdateUser("user-1", dto);

        _userTagService.Verify(s => s.AssignTagsAsync(
            It.IsAny<string>(), It.IsAny<string[]>(), It.IsAny<CancellationToken>()), Times.Never);
    }

    [Fact]
    public async Task UpdateUser_IdentityFailure_Returns400()
    {
        var user = new ApplicationUser { Id = "user-1" };
        _userManager.Setup(m => m.FindByIdAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Failed(new IdentityError { Description = "Update failed" }));

        var result = await _controller.UpdateUser("user-1", new UpdateUserDto(null, null, null, null));

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task UpdateUser_NullDto_OnlyPersistsWithNoChanges()
    {
        var user = new ApplicationUser
        {
            Id            = "user-1",
            Tags          = new List<string> { "tech" },
            MutedTags     = new List<string> { "ads" },
            Clubs         = new List<string> { "club-1" },
            MatchingScore = 0.5
        };
        _userManager.Setup(m => m.FindByIdAsync("user-1")).ReturnsAsync(user);
        _userManager.Setup(m => m.UpdateAsync(It.IsAny<ApplicationUser>()))
            .ReturnsAsync(IdentityResult.Success);

        // All fields are null → nothing should change
        var result = await _controller.UpdateUser("user-1", new UpdateUserDto(null, null, null, null));

        Assert.IsType<OkObjectResult>(result);
        _userTagService.Verify(s => s.AssignTagsAsync(
            It.IsAny<string>(), It.IsAny<string[]>(), It.IsAny<CancellationToken>()), Times.Never);
    }
}
