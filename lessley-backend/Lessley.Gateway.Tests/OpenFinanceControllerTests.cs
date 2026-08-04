using System.Reflection;
using System.Security.Claims;
using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Controllers;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using Xunit;

namespace Lessley.Gateway.Tests;

// Regression guard for the critical pre-auth financial-data IDOR: OpenFinanceController
// must require authentication and must only ever act on the caller's own identity.
public class OpenFinanceControllerTests
{
    private readonly Mock<IOpenFinanceService> _openFinanceService = new();
    private readonly OpenFinanceController _controller;

    private const string CallerEmail = "caller@test.com";

    public OpenFinanceControllerTests()
    {
        _controller = new OpenFinanceController(_openFinanceService.Object);

        var identity = new ClaimsIdentity(new[]
        {
            new Claim(ClaimTypes.NameIdentifier, "caller-id"),
            new Claim(ClaimTypes.Email, CallerEmail),
        }, "Bearer");
        _controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext { User = new ClaimsPrincipal(identity) }
        };
    }

    [Fact]
    public void Controller_RequiresAuthorization()
    {
        var authorize = typeof(OpenFinanceController).GetCustomAttribute<AuthorizeAttribute>();
        Assert.NotNull(authorize);
    }

    [Fact]
    public void Controller_HasNoAnonymousActions()
    {
        var actions = typeof(OpenFinanceController)
            .GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly);

        Assert.All(actions, m =>
            Assert.Null(m.GetCustomAttribute<AllowAnonymousAttribute>()));
    }

    [Fact]
    public async Task CreateAccessToken_UsesCallerEmailFromJwt()
    {
        _openFinanceService
            .Setup(s => s.CreateAccessToken(CallerEmail))
            .ReturnsAsync("token");

        var result = await _controller.CreateAccessToken();

        Assert.IsType<OkObjectResult>(result);
        _openFinanceService.Verify(s => s.CreateAccessToken(CallerEmail), Times.Once);
    }

    [Fact]
    public async Task GetTransactions_UsesCallerEmailFromJwt()
    {
        _openFinanceService
            .Setup(s => s.GetTransactions(CallerEmail))
            .ReturnsAsync(new OBTransactionsResponse());

        var result = await _controller.GetTransactions();

        Assert.IsType<OkObjectResult>(result);
        _openFinanceService.Verify(s => s.GetTransactions(CallerEmail), Times.Once);
    }

    [Fact]
    public async Task CreateNewConnection_UsesCallerEmailFromJwt()
    {
        _openFinanceService
            .Setup(s => s.InitiateConnectionJourney(CallerEmail, It.IsAny<string?>()))
            .ReturnsAsync(new ConnectionResponse { ConnectUrl = "https://connect.example/journey" });

        var result = await _controller.CreateNewConnection();

        Assert.IsType<RedirectResult>(result);
        _openFinanceService.Verify(s => s.InitiateConnectionJourney(CallerEmail, It.IsAny<string?>()), Times.Once);
    }
}
