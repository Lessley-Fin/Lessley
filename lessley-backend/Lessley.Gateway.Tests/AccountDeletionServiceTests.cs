using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Classes;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Xunit;

namespace Lessley.Gateway.Tests;

public class AccountDeletionServiceTests
{
    private const string Email    = "user@test.com";
    private const string UserName = "tester";

    private readonly Mock<UserManager<ApplicationUser>> _userManager;
    private readonly Mock<SignInManager<ApplicationUser>> _signInManager;
    private readonly Mock<IOpenFinanceService> _openFinance = new();
    private readonly Mock<INotificationRepository> _notifications = new();
    private readonly Mock<IAuthSessionService> _sessions = new();
    private readonly Mock<IPendingRegistrationRepository> _pendingRegistrations = new();
    private readonly Mock<IVerificationCodeRepository> _verificationCodes = new();
    private readonly Mock<IConnectionManager> _connectionManager = new();
    private readonly AccountDeletionService _service;

    private readonly ApplicationUser _user = new()
    {
        Id                 = "user-id",
        UserName           = UserName,
        NormalizedUserName = "TESTER",
        Email              = Email,
        NormalizedEmail    = "USER@TEST.COM",
    };

    public AccountDeletionServiceTests()
    {
        var store = new Mock<IUserStore<ApplicationUser>>();
        _userManager = new Mock<UserManager<ApplicationUser>>(
            store.Object, null!, null!, null!, null!, null!, null!, null!, null!);

        _signInManager = new Mock<SignInManager<ApplicationUser>>(
            _userManager.Object,
            new Mock<IHttpContextAccessor>().Object,
            new Mock<IUserClaimsPrincipalFactory<ApplicationUser>>().Object,
            null!, null!, null!, null!);

        _userManager.Setup(m => m.FindByEmailAsync(Email)).ReturnsAsync(_user);
        _userManager.Setup(m => m.DeleteAsync(_user)).ReturnsAsync(IdentityResult.Success);
        _connectionManager.Setup(c => c.GetConnections(Email)).Returns(Array.Empty<string>());

        _service = new AccountDeletionService(
            _userManager.Object,
            _signInManager.Object,
            _openFinance.Object,
            _notifications.Object,
            _sessions.Object,
            _pendingRegistrations.Object,
            _verificationCodes.Object,
            _connectionManager.Object,
            NullLogger<AccountDeletionService>.Instance);
    }

    private void PasswordCheckReturns(SignInResult result) =>
        _signInManager
            .Setup(s => s.CheckPasswordSignInAsync(_user, It.IsAny<string>(), true))
            .ReturnsAsync(result);

    private static DeleteAccountDto Dto(
        string identifier = UserName, string password = "correct-horse", bool closeConnection = false)
        => new()
        {
            UserNameOrEmail            = identifier,
            Password                   = password,
            CloseOpenFinanceConnection = closeConnection,
        };

    private void AssertNothingDeleted()
    {
        _userManager.Verify(m => m.DeleteAsync(It.IsAny<ApplicationUser>()), Times.Never);
        _notifications.Verify(n => n.DeleteByUserAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()), Times.Never);
        _sessions.Verify(s => s.DeleteAllRefreshTokensAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()), Times.Never);
    }

    [Fact]
    public async Task DeleteAsync_UnknownCaller_ReturnsNotFound()
    {
        _userManager.Setup(m => m.FindByEmailAsync("ghost@test.com")).ReturnsAsync((ApplicationUser?)null);

        var result = await _service.DeleteAsync("ghost@test.com", Dto());

        Assert.IsType<AccountDeletionResult.NotFoundResult>(result);
        AssertNothingDeleted();
    }

    [Fact]
    public async Task DeleteAsync_IdentifierDoesNotMatchCaller_ReturnsInvalidAndSkipsPasswordCheck()
    {
        var result = await _service.DeleteAsync(Email, Dto(identifier: "someone-else"));

        Assert.IsType<AccountDeletionResult.InvalidCredentials>(result);
        _signInManager.Verify(
            s => s.CheckPasswordSignInAsync(It.IsAny<ApplicationUser>(), It.IsAny<string>(), It.IsAny<bool>()),
            Times.Never);
        AssertNothingDeleted();
    }

    [Theory]
    [InlineData(UserName)]
    [InlineData(Email)]
    [InlineData("TESTER")]
    [InlineData("  user@test.com  ")]
    public async Task DeleteAsync_AcceptsEitherIdentifierRegardlessOfCaseOrPadding(string identifier)
    {
        PasswordCheckReturns(SignInResult.Success);

        var result = await _service.DeleteAsync(Email, Dto(identifier: identifier));

        Assert.IsType<AccountDeletionResult.Success>(result);
    }

    [Fact]
    public async Task DeleteAsync_WrongPassword_ReturnsInvalid()
    {
        PasswordCheckReturns(SignInResult.Failed);

        var result = await _service.DeleteAsync(Email, Dto());

        Assert.IsType<AccountDeletionResult.InvalidCredentials>(result);
        AssertNothingDeleted();
    }

    [Fact]
    public async Task DeleteAsync_LockedOut_ReturnsLockedOut()
    {
        PasswordCheckReturns(SignInResult.LockedOut);

        var result = await _service.DeleteAsync(Email, Dto());

        Assert.IsType<AccountDeletionResult.LockedOut>(result);
        AssertNothingDeleted();
    }

    [Fact]
    public async Task DeleteAsync_OpenFinanceUnreachable_DeletesNothing()
    {
        PasswordCheckReturns(SignInResult.Success);
        _openFinance
            .Setup(o => o.CloseAllConnectionsAsync(Email, It.IsAny<CancellationToken>()))
            .ThrowsAsync(new HttpRequestException("provider down"));

        var result = await _service.DeleteAsync(Email, Dto(closeConnection: true));

        Assert.IsType<AccountDeletionResult.OpenFinanceFailed>(result);
        AssertNothingDeleted();
    }

    [Fact]
    public async Task DeleteAsync_WithoutClosingConnection_LeavesOpenFinanceAlone()
    {
        PasswordCheckReturns(SignInResult.Success);

        var result = await _service.DeleteAsync(Email, Dto(closeConnection: false));

        Assert.IsType<AccountDeletionResult.Success>(result);
        _openFinance.Verify(
            o => o.CloseAllConnectionsAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()), Times.Never);
        _userManager.Verify(m => m.DeleteAsync(_user), Times.Once);
    }

    [Fact]
    public async Task DeleteAsync_Success_PurgesEveryCollectionKeyedToTheUser()
    {
        PasswordCheckReturns(SignInResult.Success);
        _connectionManager.Setup(c => c.GetConnections(Email)).Returns(new[] { "conn-1", "conn-2" });

        var result = await _service.DeleteAsync(Email, Dto(closeConnection: true));

        Assert.IsType<AccountDeletionResult.Success>(result);
        _openFinance.Verify(o => o.CloseAllConnectionsAsync(Email, It.IsAny<CancellationToken>()), Times.Once);

        // Notifications are keyed by email, refresh tokens by the Identity id — using one value
        // for both is the mistake this asserts against.
        _notifications.Verify(n => n.DeleteByUserAsync(Email, It.IsAny<CancellationToken>()), Times.Once);
        _sessions.Verify(s => s.DeleteAllRefreshTokensAsync("user-id", It.IsAny<CancellationToken>()), Times.Once);

        _pendingRegistrations.Verify(
            p => p.DeleteByEmailOrUserNameAsync("USER@TEST.COM", "TESTER", It.IsAny<CancellationToken>()), Times.Once);
        _verificationCodes.Verify(
            v => v.DeleteByEmailAsync("USER@TEST.COM", It.IsAny<CancellationToken>()), Times.Once);

        _connectionManager.Verify(c => c.RemoveConnection(Email, "conn-1"), Times.Once);
        _connectionManager.Verify(c => c.RemoveConnection(Email, "conn-2"), Times.Once);

        _userManager.Verify(m => m.DeleteAsync(_user), Times.Once);
    }

    [Fact]
    public async Task DeleteAsync_IdentityRefusesTheDelete_Throws()
    {
        PasswordCheckReturns(SignInResult.Success);
        _userManager
            .Setup(m => m.DeleteAsync(_user))
            .ReturnsAsync(IdentityResult.Failed(new IdentityError { Description = "concurrency failure" }));

        await Assert.ThrowsAsync<InvalidOperationException>(() => _service.DeleteAsync(Email, Dto()));
    }
}
