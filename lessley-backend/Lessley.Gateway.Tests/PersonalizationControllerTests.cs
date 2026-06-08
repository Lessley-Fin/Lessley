using Lessley.Gateway.Api.Controllers;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Mvc;
using Moq;
using Xunit;

namespace Lessley.Gateway.Tests;

public class PersonalizationControllerTests
{
    private readonly Mock<IPersonalizationService> _service = new();
    private readonly PersonalizationController _controller;

    public PersonalizationControllerTests()
    {
        _controller = new PersonalizationController(_service.Object);
    }

    [Fact]
    public async Task RequestClubRecommendations_Returns202AndTriggersAsync()
    {
        _service.Setup(s => s.RequestClubRecommendationsAsync("a@b.com", It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var result = await _controller.RequestClubRecommendations("a@b.com", CancellationToken.None);

        Assert.IsType<AcceptedResult>(result);
        _service.Verify(s => s.RequestClubRecommendationsAsync("a@b.com", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task GetPreferredAccounts_ProxiesAndReturnsJson()
    {
        _service.Setup(s => s.GetPreferredAccountsAsync("a@b.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync("{\"accounts\":[]}");

        var result = await _controller.GetPreferredAccounts("a@b.com", CancellationToken.None);

        var content = Assert.IsType<ContentResult>(result);
        Assert.Equal("application/json", content.ContentType);
        Assert.Equal("{\"accounts\":[]}", content.Content);
        _service.Verify(s => s.GetPreferredAccountsAsync("a@b.com", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task GetPreferredStores_DelegatesToService()
    {
        _service.Setup(s => s.GetPreferredStoresAsync("a@b.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync("[]");

        var result = await _controller.GetPreferredStores("a@b.com", CancellationToken.None);

        Assert.IsType<ContentResult>(result);
        _service.Verify(s => s.GetPreferredStoresAsync("a@b.com", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task GetAlternativeStores_DelegatesToService()
    {
        _service.Setup(s => s.GetAlternativeStoresAsync("a@b.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync("[]");

        var result = await _controller.GetAlternativeStores("a@b.com", CancellationToken.None);

        Assert.IsType<ContentResult>(result);
        _service.Verify(s => s.GetAlternativeStoresAsync("a@b.com", It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task GetTransactionBreakdownByMcc_DelegatesToService()
    {
        _service.Setup(s => s.GetTransactionBreakdownByMccAsync("a@b.com", It.IsAny<CancellationToken>()))
            .ReturnsAsync("[]");

        var result = await _controller.GetTransactionBreakdownByMcc("a@b.com", CancellationToken.None);

        Assert.IsType<ContentResult>(result);
        _service.Verify(s => s.GetTransactionBreakdownByMccAsync("a@b.com", It.IsAny<CancellationToken>()), Times.Once);
    }
}
