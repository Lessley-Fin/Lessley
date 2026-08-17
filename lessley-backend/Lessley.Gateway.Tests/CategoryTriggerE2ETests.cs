using System.Net;
using System.Net.Http.Json;
using Lessley.Gateway.Api.Models;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace Lessley.Gateway.Tests;

/// <summary>
/// Which events ask Personalization to recalculate a user's categories.
///
/// The Gateway is the only writer of the Tags field, and it only ever writes what comes back
/// from a recalculation — so a missing trigger shows up as categories that silently stop
/// updating, and a spurious one spends an Open Finance round trip to arrive at the same
/// answer. Both are invisible in production, which is what these tests are for.
/// </summary>
public class CategoryTriggerE2ETests : IClassFixture<GatewayWebApplicationFactory>
{
    private readonly GatewayWebApplicationFactory _factory;

    public CategoryTriggerE2ETests(GatewayWebApplicationFactory factory)
    {
        _factory = factory;
    }

    [Fact]
    public async Task ChangingTheMatchLevel_TriggersARecalculation()
    {
        var email = await CreateUserAsync();
        _factory.PersonalizationService.ClearCategoryTriggers();

        var response = await PatchProfileAsync(email, new UpdateUserDto(null, null, "High"));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Contains(email, _factory.PersonalizationService.CategoryTriggers);
    }

    [Fact]
    public async Task MutingACategory_DoesNotTriggerARecalculation()
    {
        // Muting is applied when notifications fan out and when the client renders, never in
        // the calculation — recomputing here would return exactly the same categories.
        var email = await CreateUserAsync();
        _factory.PersonalizationService.ClearCategoryTriggers();

        var response = await PatchProfileAsync(email, new UpdateUserDto(new List<string> { "GROCERIES" }, null, null));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.DoesNotContain(email, _factory.PersonalizationService.CategoryTriggers);
    }

    [Fact]
    public async Task ChangingClubs_DoesNotTriggerARecalculation()
    {
        // Clubs decide which missed-savings alternatives a user can act on, not what they spend on.
        var email = await CreateUserAsync();
        _factory.PersonalizationService.ClearCategoryTriggers();

        var response = await PatchProfileAsync(email, new UpdateUserDto(null, new List<string> { "clubA" }, null));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.DoesNotContain(email, _factory.PersonalizationService.CategoryTriggers);
    }

    [Fact]
    public async Task ResavingTheSameMatchLevel_DoesNotTriggerARecalculation()
    {
        var email = await CreateUserAsync();
        await PatchProfileAsync(email, new UpdateUserDto(null, null, "High"));

        _factory.PersonalizationService.ClearCategoryTriggers();
        var response = await PatchProfileAsync(email, new UpdateUserDto(null, null, "High"));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.DoesNotContain(email, _factory.PersonalizationService.CategoryTriggers);
    }

    private async Task<HttpResponseMessage> PatchProfileAsync(string email, UpdateUserDto dto)
    {
        var token = NotificationE2ETests.BuildJwt($"trigger-{Guid.NewGuid():N}", "Admin", email);

        using var http = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new("Bearer", token);

        return await http.PatchAsJsonAsync("api/user/me", dto);
    }

    private async Task<string> CreateUserAsync()
    {
        using var scope = _factory.Services.CreateScope();
        var userManager = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();

        var email = $"trigger-{Guid.NewGuid():N}@test.com";
        var user  = new ApplicationUser { UserName = email, Email = email };
        await userManager.CreateAsync(user, "Test1234!");
        return email;
    }
}
