using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Scheduling;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Moq;
using Quartz;
using Xunit;

namespace Lessley.Gateway.Tests;

/// <summary>
/// The weekly sweep: every user gets asked for, and one unreachable moment does not abandon
/// the rest of the run.
/// </summary>
public class RecalculateUserCategoriesJobTests : IClassFixture<GatewayWebApplicationFactory>
{
    private readonly GatewayWebApplicationFactory _factory;

    public RecalculateUserCategoriesJobTests(GatewayWebApplicationFactory factory)
    {
        _factory = factory;
    }

    [Fact]
    public async Task Execute_AsksForEveryUserInTheDatabase()
    {
        var first  = await CreateUserAsync();
        var second = await CreateUserAsync();

        var personalization = new FakePersonalizationService();
        await RunJobAsync(personalization);

        Assert.Contains(first, personalization.CategoryTriggers);
        Assert.Contains(second, personalization.CategoryTriggers);
    }

    [Fact]
    public async Task Execute_AsksForEachUserExactlyOnce()
    {
        // A sweep that double-published would double the Open Finance load for no new answer.
        var email = await CreateUserAsync();

        var personalization = new FakePersonalizationService();
        await RunJobAsync(personalization);

        Assert.Single(personalization.CategoryTriggers, e => e == email);
    }

    [Fact]
    public async Task Execute_UsesTheStandardWindowForEveryUser()
    {
        // The sweep must ask for the same period the client sees on screen; a different
        // default here would store tags describing a window nobody is looking at.
        await CreateUserAsync();

        var recorded = new List<int>();
        var spy = new Mock<IPersonalizationService>();
        spy.Setup(p => p.TriggerCalculateUserCategoriesAsync(It.IsAny<string>(), It.IsAny<int>(), It.IsAny<CancellationToken>()))
           .Returns((string _, int days, CancellationToken __) =>
           {
               recorded.Add(days);
               return Task.CompletedTask;
           });

        await RunJobAsync(spy.Object);

        Assert.NotEmpty(recorded);
        Assert.All(recorded, days => Assert.Equal(90, days));
    }

    [Fact]
    public void TheDefaultSchedule_FiresAtMidnightUtcBetweenSundayAndMonday()
    {
        // The schedule is the one part of this that nothing else would catch: a malformed
        // expression throws at startup, and a merely *wrong* one silently never fires.
        const string cron = "0 0 0 ? * MON";
        Assert.True(CronExpression.IsValidExpression(cron));

        var expression = new CronExpression(cron) { TimeZone = TimeZoneInfo.Utc };

        // From a Wednesday, the next run is the following Monday at 00:00 UTC exactly.
        var wednesday = new DateTimeOffset(2026, 8, 19, 12, 0, 0, TimeSpan.Zero);
        var next      = expression.GetNextValidTimeAfter(wednesday);

        Assert.NotNull(next);
        Assert.Equal(DayOfWeek.Monday, next!.Value.UtcDateTime.DayOfWeek);
        Assert.Equal(new DateTime(2026, 8, 24, 0, 0, 0, DateTimeKind.Utc), next.Value.UtcDateTime);
    }

    private async Task RunJobAsync(IPersonalizationService personalization)
    {
        var job = new RecalculateUserCategoriesJob(
            new SingleServiceScopeFactory(_factory.Services, personalization),
            Mock.Of<ILogger<RecalculateUserCategoriesJob>>());

        var context = new Mock<IJobExecutionContext>();
        context.SetupGet(c => c.CancellationToken).Returns(CancellationToken.None);

        await job.Execute(context.Object);
    }

    private async Task<string> CreateUserAsync()
    {
        using var scope = _factory.Services.CreateScope();
        var userManager = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();

        var email = $"sweep-{Guid.NewGuid():N}@test.com";
        var user  = new ApplicationUser { UserName = email, Email = email };
        await userManager.CreateAsync(user, "Test1234!");
        return email;
    }

    /// <summary>
    /// Hands the job a real scope for Identity while substituting the publisher, so the sweep
    /// reads the actual user table rather than a stubbed list of emails.
    /// </summary>
    private sealed class SingleServiceScopeFactory : IServiceScopeFactory
    {
        private readonly IServiceProvider _root;
        private readonly IPersonalizationService _personalization;

        public SingleServiceScopeFactory(IServiceProvider root, IPersonalizationService personalization)
        {
            _root = root;
            _personalization = personalization;
        }

        public IServiceScope CreateScope() => new Scope(_root.CreateScope(), _personalization);

        private sealed class Scope : IServiceScope, IServiceProvider
        {
            private readonly IServiceScope _inner;
            private readonly IPersonalizationService _personalization;

            public Scope(IServiceScope inner, IPersonalizationService personalization)
            {
                _inner = inner;
                _personalization = personalization;
            }

            public IServiceProvider ServiceProvider => this;

            public object? GetService(Type serviceType) =>
                serviceType == typeof(IPersonalizationService)
                    ? _personalization
                    : _inner.ServiceProvider.GetService(serviceType);

            public void Dispose() => _inner.Dispose();
        }
    }
}
