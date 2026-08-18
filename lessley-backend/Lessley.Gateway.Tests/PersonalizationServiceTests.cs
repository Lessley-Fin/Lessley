using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Services.Classes;
using MassTransit;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;

namespace Lessley.Gateway.Tests;

/// <summary>
/// The category-recalculation trigger: what it publishes, and what it does when it can't.
/// </summary>
public class PersonalizationServiceTests
{
    private readonly Mock<IPublishEndpoint> _bus = new();
    private readonly PersonalizationService _service;

    public PersonalizationServiceTests()
    {
        _service = new PersonalizationService(_bus.Object, Mock.Of<ILogger<PersonalizationService>>());
    }

    [Fact]
    public async Task TriggerCalculateUserCategories_PublishesTheCommandForThatUser()
    {
        await _service.TriggerCalculateUserCategoriesAsync("user@test.com", days: 90);

        _bus.Verify(b => b.Publish(
            It.Is<CalculateUserCategoriesCommand>(c => c.UserId == "user@test.com" && c.Days == 90),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task TriggerCalculateUserCategories_DefaultsToTheStandardWindow()
    {
        // 90 days mirrors Personalization's LIMITS.DAYS. A caller that does not care about the
        // window must still get the same one the client sees on screen.
        await _service.TriggerCalculateUserCategoriesAsync("user@test.com");

        _bus.Verify(b => b.Publish(
            It.Is<CalculateUserCategoriesCommand>(c => c.Days == 90),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task TriggerCalculateUserCategories_SwallowsAPublishFailure()
    {
        // Callers are finishing a signup, a bank journey or a settings save. None of those
        // should fail because the bus is unreachable — the stored categories stay valid, and
        // the next trigger recomputes them.
        _bus.Setup(b => b.Publish(It.IsAny<CalculateUserCategoriesCommand>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("broker unreachable"));

        var thrown = await Record.ExceptionAsync(
            () => _service.TriggerCalculateUserCategoriesAsync("user@test.com"));

        Assert.Null(thrown);
    }
}
