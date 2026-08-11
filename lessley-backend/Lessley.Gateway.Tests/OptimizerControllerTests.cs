using System.Net;
using System.Net.Http.Json;
using System.Security.Claims;
using Lessley.Gateway.Api.Controllers;
using Lessley.Gateway.Api.Models.Club;
using Lessley.Gateway.Api.Models.Optimizer;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Xunit;

namespace Lessley.Gateway.Tests;

public class OptimizerControllerTests
{
    private readonly Mock<IOptimizerProxyService> _proxy = new();
    private readonly Mock<IUserService> _userService = new();
    private readonly OptimizerController _controller;

    /// <summary>What the proxy was actually asked to send on to the Python service.</summary>
    private OptimizeRequestDto? _forwarded;

    public OptimizerControllerTests()
    {
        _controller = new OptimizerController(
            _proxy.Object,
            _userService.Object,
            NullLogger<OptimizerController>.Instance);

        var identity = new ClaimsIdentity(new[]
        {
            new Claim(ClaimTypes.NameIdentifier, "caller-id"),
            new Claim(ClaimTypes.Email, "user@test.com"),
        }, "Bearer");
        _controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext { User = new ClaimsPrincipal(identity) }
        };

        _proxy
            .Setup(p => p.OptimizeAsync(It.IsAny<OptimizeRequestDto>(), It.IsAny<CancellationToken>()))
            .Callback<OptimizeRequestDto, CancellationToken>((r, _) => _forwarded = r)
            .ReturnsAsync(new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = JsonContent.Create(new { results = Array.Empty<object>() }),
            });
    }

    private void UserHasClubs(params string[] clubs) =>
        _userService
            .Setup(s => s.GetUserClubsAsync("user@test.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync(clubs.ToList());

    private static OptimizeRequestDto Request(params string[] memberSourceIds) => new()
    {
        StoreId         = "store_1",
        CartTotal       = 100,
        MemberSourceIds = memberSourceIds.ToList(),
    };

    [Fact]
    public async Task Optimize_TranslatesTheUsersClubsIntoSourceIds()
    {
        UserHasClubs("club_hot", "club_mastercard");

        await _controller.Optimize(Request(), CancellationToken.None);

        Assert.Equal(new[] { "hot", "mastercard" }, _forwarded!.MemberSourceIds);
    }

    [Fact]
    public async Task Optimize_IgnoresMembershipsClaimedByTheClient()
    {
        // The point of resolving server-side: a caller must not unlock members-only
        // deals by asserting a club it never joined.
        UserHasClubs("club_hot");

        await _controller.Optimize(Request("mastercard", "behatsdaa"), CancellationToken.None);

        Assert.Equal(new[] { "hot" }, _forwarded!.MemberSourceIds);
    }

    [Fact]
    public async Task Optimize_UserWithNoClubs_ForwardsAnEmptyList()
    {
        // A user who has joined nothing is the default state of every new account,
        // so this is the common path, not an edge case.
        UserHasClubs();

        await _controller.Optimize(Request("hot"), CancellationToken.None);

        Assert.Empty(_forwarded!.MemberSourceIds);
    }

    [Fact]
    public async Task Optimize_UserNotFound_Returns404()
    {
        _userService
            .Setup(s => s.GetUserClubsAsync("user@test.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync((List<string>?)null);

        var result = await _controller.Optimize(Request(), CancellationToken.None);

        Assert.IsType<NotFoundObjectResult>(result);
        _proxy.Verify(
            p => p.OptimizeAsync(It.IsAny<OptimizeRequestDto>(), It.IsAny<CancellationToken>()),
            Times.Never);
    }

    [Fact]
    public async Task Optimize_MissingStoreId_Returns400()
    {
        var result = await _controller.Optimize(new OptimizeRequestDto { CartTotal = 100 }, CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task Optimize_OptimizerUnreachable_Returns503()
    {
        UserHasClubs("club_hot");
        _proxy
            .Setup(p => p.OptimizeAsync(It.IsAny<OptimizeRequestDto>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new HttpRequestException("connection refused"));

        var result = await _controller.Optimize(Request(), CancellationToken.None);

        var status = Assert.IsType<ObjectResult>(result);
        Assert.Equal(StatusCodes.Status503ServiceUnavailable, status.StatusCode);
    }
}

public class ClubSourceIdsTests
{
    [Theory]
    [InlineData("club_hot", "hot")]
    [InlineData("club_mastercard", "mastercard")]
    [InlineData("club_hever_gift_card_company", "hever_gift_card_company")]
    [InlineData("club_paisplus_food_chains", "paisplus_food_chains")]
    public void FromClubIds_StripsTheClubPrefix(string clubId, string expected) =>
        Assert.Equal(new[] { expected }, ClubSourceIds.FromClubIds(new[] { clubId }));

    [Fact]
    public void FromClubIds_LeavesABareSourceIdAlone() =>
        Assert.Equal(new[] { "hot" }, ClubSourceIds.FromClubIds(new[] { "hot" }));

    [Fact]
    public void FromClubIds_DropsBlanksAndDeDupesPreservingOrder() =>
        Assert.Equal(
            new[] { "hot", "topcash" },
            ClubSourceIds.FromClubIds(new[] { "club_hot", "  ", "hot", "club_topcash", "" }));

    [Fact]
    public void FromClubIds_NullIsEmpty() => Assert.Empty(ClubSourceIds.FromClubIds(null));
}
