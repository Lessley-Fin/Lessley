using System.Security.Claims;
using Lessley.Gateway.Api.Controllers;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using Xunit;

namespace Lessley.Gateway.Tests;

public class UserControllerTests
{
    private readonly Mock<IUserService> _userService = new();
    private readonly Mock<IOpenFinanceService> _openFinanceService = new();
    private readonly Mock<IPersonalizationService> _personalizationService = new();
    private readonly Mock<INotificationService> _notificationService = new();
    private readonly UserController _controller;

    public UserControllerTests()
    {
        _controller = new UserController(
            _userService.Object,
            _openFinanceService.Object,
            _personalizationService.Object,
            _notificationService.Object);

        SetCallerContext("user@test.com", "Admin");
    }

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

    // ── UpdateUser (PATCH /api/user/me) ───────────────────────────────────────

    [Fact]
    public async Task UpdateUser_UserNotFound_Returns404()
    {
        _userService
            .Setup(s => s.UpdateAsync("user@test.com", It.IsAny<UpdateUserDto>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(UserOperationResult.NotFound());

        var result = await _controller.UpdateUser(new UpdateUserDto(null, null, null));

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task UpdateUser_Success_Returns200()
    {
        _userService
            .Setup(s => s.UpdateAsync("user@test.com", It.IsAny<UpdateUserDto>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(UserOperationResult.Ok(new { email = "user@test.com" }));

        var dto    = new UpdateUserDto(new List<string> { "sports" }, new List<string> { "club-a" }, "High");
        var result = await _controller.UpdateUser(dto);

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public async Task UpdateUser_BadRequest_Returns400()
    {
        _userService
            .Setup(s => s.UpdateAsync("user@test.com", It.IsAny<UpdateUserDto>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(UserOperationResult.BadRequest(new { error = "Update failed" }));

        var result = await _controller.UpdateUser(new UpdateUserDto(null, null, null));

        Assert.IsType<BadRequestObjectResult>(result);
    }

    // ── TriggerMissedSavings (POST /api/user/recommendations/missed-savings) ──

    [Fact]
    public async Task TriggerMissedSavings_UserWithCategories_Returns202()
    {
        _userService
            .Setup(s => s.GetUserTagsAsync("user@test.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync(new List<string> { "5411" });

        var result = await _controller.TriggerMissedSavings(ct: CancellationToken.None);

        Assert.IsType<AcceptedResult>(result);
        _personalizationService.Verify(
            s => s.TriggerCalculateMissedSavingsAsync("user@test.com", true, 7, It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task TriggerMissedSavings_UserNotFound_Returns404()
    {
        _userService
            .Setup(s => s.GetUserTagsAsync("user@test.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync((List<string>?)null);

        var result = await _controller.TriggerMissedSavings(ct: CancellationToken.None);

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task TriggerMissedSavings_NoCategories_Returns422()
    {
        _userService
            .Setup(s => s.GetUserTagsAsync("user@test.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync(new List<string>());

        var result = await _controller.TriggerMissedSavings(ct: CancellationToken.None);

        Assert.IsType<UnprocessableEntityObjectResult>(result);
    }

    // ── TriggerMatchingClubs (POST /api/user/recommendations/matching-clubs) ──

    [Fact]
    public async Task TriggerMatchingClubs_UserWithCategories_Returns202()
    {
        _userService
            .Setup(s => s.GetUserTagsAsync("user@test.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync(new List<string> { "5411" });

        var result = await _controller.TriggerMatchingClubs(CancellationToken.None);

        Assert.IsType<AcceptedResult>(result);
        _personalizationService.Verify(
            s => s.TriggerCalculateMatchingClubsAsync("user@test.com", It.IsAny<CancellationToken>()),
            Times.Once);
    }

}
