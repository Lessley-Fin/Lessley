using System.Security.Claims;
using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Controllers;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using Moq;
using Xunit;

namespace Lessley.Gateway.Tests;

public class UserControllerTests
{
    private readonly Mock<IUserService> _userService = new();
    private readonly Mock<IOpenFinanceService> _openFinanceService = new();
    private readonly UserController _controller;

    public UserControllerTests()
    {
        _controller = new UserController(
            _userService.Object,
            _openFinanceService.Object,
            Options.Create(new AuthConfig()));

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

    // ── DeleteMyAccount (DELETE /api/user/me) ─────────────────────────────────

    private void DeletionReturns(AccountDeletionResult result) =>
        _userService
            .Setup(s => s.DeleteMyAccountAsync("user@test.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync(result);

    [Fact]
    public async Task DeleteMyAccount_Success_Returns204AndClearsTheAuthCookies()
    {
        DeletionReturns(AccountDeletionResult.Ok());

        var result = await _controller.DeleteMyAccount();

        Assert.IsType<NoContentResult>(result);

        // Deleting the cookies means expiring them, which shows up as Set-Cookie headers.
        var setCookies = _controller.Response.Headers["Set-Cookie"].ToString();
        Assert.Contains("access_token=", setCookies);
        Assert.Contains("refresh_token=", setCookies);
    }

    [Fact]
    public async Task DeleteMyAccount_TakesTheEmailFromTheJwtAndNothingElse()
    {
        // The action has no body parameter at all, so the deleted account can only ever be the
        // one the token names — asserted here so a "convenience" DTO cannot creep back in.
        DeletionReturns(AccountDeletionResult.Ok());

        await _controller.DeleteMyAccount();

        _userService.Verify(
            s => s.DeleteMyAccountAsync("user@test.com", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task DeleteMyAccount_OpenFinanceFailed_Returns502()
    {
        DeletionReturns(AccountDeletionResult.OpenFinance("provider down"));

        var result = await _controller.DeleteMyAccount();

        Assert.Equal(StatusCodes.Status502BadGateway, Assert.IsType<ObjectResult>(result).StatusCode);
    }

    [Fact]
    public async Task DeleteMyAccount_UserNotFound_Returns404()
    {
        DeletionReturns(AccountDeletionResult.NotFound());

        var result = await _controller.DeleteMyAccount();

        Assert.IsType<NotFoundObjectResult>(result);
    }
}
