using System.Net;
using Xunit;

namespace Lessley.Gateway.Tests;

public class PersonalizationE2ETests : IClassFixture<GatewayWebApplicationFactory>
{
    private readonly GatewayWebApplicationFactory _factory;

    public PersonalizationE2ETests(GatewayWebApplicationFactory factory)
    {
        _factory = factory;
    }

    [Theory]
    [InlineData("api/personalization/accounts/user@test.com")]
    [InlineData("api/personalization/stores/user@test.com")]
    [InlineData("api/personalization/alternative-stores/user@test.com")]
    [InlineData("api/personalization/transactions-breakdown/user@test.com")]
    public async Task ReadOnlyProxy_WithToken_Returns200(string path)
    {
        var token = NotificationE2ETests.BuildJwt("reader", "Viewer");
        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", token);

        var response = await http.GetAsync(path);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("[]", await response.Content.ReadAsStringAsync());
    }

    [Fact]
    public async Task ClubRecommendations_Async_Returns202AndTriggers()
    {
        var token = NotificationE2ETests.BuildJwt("club-reader", "Viewer");
        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", token);

        var before   = _factory.PersonalizationService.ClubRecommendationCallCount;
        var response = await http.PostAsync("api/personalization/club-recommendations/user@test.com", null);

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);
        Assert.True(_factory.PersonalizationService.ClubRecommendationCallCount > before);
    }

    [Theory]
    [InlineData("api/personalization/accounts/user@test.com")]
    [InlineData("api/personalization/stores/user@test.com")]
    [InlineData("api/personalization/alternative-stores/user@test.com")]
    [InlineData("api/personalization/transactions-breakdown/user@test.com")]
    public async Task ReadOnlyProxy_WithoutToken_Returns401(string path)
    {
        using var http = _factory.CreateClient();

        var response = await http.GetAsync(path);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }
}
