using System.Net;
using System.Net.Http.Json;
using System.Text;
using Lessley.Gateway.Api.Models.Interest;
using Microsoft.AspNetCore.Hosting;
using MongoDB.Bson;
using MongoDB.Driver;
using Xunit;

namespace Lessley.Gateway.Tests;

/// <summary>
/// The Testing host uses InMemory EF, but the interest pipeline is pure MongoDB — and the
/// property that matters most (a retried flush stores nothing twice) is enforced by a unique
/// index, which no fake can stand in for.
/// </summary>
/// <remarks>
/// Set <c>MONGODB_URL</c> to run these; without it every test returns early, the same
/// convention <see cref="PipelineRealInfraE2ETests"/> uses. The index initializer is skipped
/// under <c>Testing</c>, so the fixture creates the one index under test itself.
/// </remarks>
public class InterestWebApplicationFactory : GatewayWebApplicationFactory
{
    public static readonly string? MongoUrl = Environment.GetEnvironmentVariable("MONGODB_URL");

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        base.ConfigureWebHost(builder);
        if (MongoUrl is not null)
            builder.UseSetting("ConnectionStrings:MongoDb", MongoUrl);
    }
}

public class InterestE2ETests : IClassFixture<InterestWebApplicationFactory>, IDisposable
{
    private readonly InterestWebApplicationFactory _factory;
    private readonly IMongoCollection<BsonDocument>? _events;

    /// <summary>Tags every document this class writes, so cleanup never touches anything else.</summary>
    private readonly string _sessionId = $"e2e-{Guid.NewGuid():N}";

    private static bool Available => InterestWebApplicationFactory.MongoUrl is not null;

    public InterestE2ETests(InterestWebApplicationFactory factory)
    {
        _factory = factory;
        if (!Available) return;

        var db = new MongoClient(InterestWebApplicationFactory.MongoUrl).GetDatabase("lessley");
        _events = db.GetCollection<BsonDocument>("interest_events");

        // The whole point of the duplicate test: without this index a retried flush would
        // insert twice and nothing would notice.
        _events.Indexes.CreateOne(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("event_id"),
            new CreateIndexOptions { Name = "uq_interest_event_id", Unique = true }));
    }

    [Fact]
    public async Task DuplicateEventIdInOneBatch_IsStoredOnce()
    {
        if (!Available) return;

        var eventId = Guid.NewGuid().ToString();
        var (http, _) = Authenticated();

        var response = await http.PostAsJsonAsync("api/deals/events", new InterestEventBatchDto(
        [
            Event(eventId, InterestActions.Impression, "deal-dup"),
            // Same id, different action — a retried flush replays the identical payload, but
            // storing once must be a property of the id, not of the payload matching.
            Event(eventId, InterestActions.Redirect,   "deal-dup"),
        ]));

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);

        var stored = await _events!
            .CountDocumentsAsync(Builders<BsonDocument>.Filter.Eq("event_id", eventId));

        Assert.Equal(1, stored);
    }

    [Fact]
    public async Task ResendingAnAlreadyStoredBatch_IsAcceptedAndStoresNothingNew()
    {
        if (!Available) return;

        var eventId = Guid.NewGuid().ToString();
        var (http, _) = Authenticated();
        var batch = new InterestEventBatchDto([Event(eventId, InterestActions.Open, "deal-retry")]);

        Assert.Equal(HttpStatusCode.Accepted, (await http.PostAsJsonAsync("api/deals/events", batch)).StatusCode);
        // The client could not confirm the first flush and sent it again.
        Assert.Equal(HttpStatusCode.Accepted, (await http.PostAsJsonAsync("api/deals/events", batch)).StatusCode);

        var stored = await _events!
            .CountDocumentsAsync(Builders<BsonDocument>.Filter.Eq("event_id", eventId));

        Assert.Equal(1, stored);
    }

    [Fact]
    public async Task UserIdInBody_IsIgnoredInFavourOfTheJwt()
    {
        if (!Available) return;

        var eventId = Guid.NewGuid().ToString();
        var (http, email) = Authenticated();

        // Raw JSON so the body can carry a field the DTO does not have — which is exactly what
        // an attacker would send to attribute engagement to somebody else.
        var body = $$"""
        { "events": [ {
            "eventId":    "{{eventId}}",
            "entityType": "deal",
            "entityId":   "deal-spoof",
            "action":     "redirect",
            "userId":     "victim@test.com",
            "sessionId":  "{{_sessionId}}",
            "surface":    "hot",
            "position":   0
        } ] }
        """;

        var response = await http.PostAsync("api/deals/events",
            new StringContent(body, Encoding.UTF8, "application/json"));

        Assert.Equal(HttpStatusCode.Accepted, response.StatusCode);

        var stored = await _events!
            .Find(Builders<BsonDocument>.Filter.Eq("event_id", eventId))
            .SingleAsync();

        Assert.Equal(email, stored["user_id"].AsString);
    }

    [Fact]
    public async Task BatchOverTheLimit_Is400()
    {
        if (!Available) return;

        var (http, _) = Authenticated();
        var events = Enumerable.Range(0, 51)
            .Select(i => Event(Guid.NewGuid().ToString(), InterestActions.Impression, $"deal-{i}"))
            .ToList();

        var response = await http.PostAsJsonAsync("api/deals/events", new InterestEventBatchDto(events));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task UnknownAction_Is400()
    {
        if (!Available) return;

        var (http, _) = Authenticated();
        var response = await http.PostAsJsonAsync("api/deals/events", new InterestEventBatchDto(
        [
            Event(Guid.NewGuid().ToString(), "hovered", "deal-x"),
        ]));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task WithoutAToken_Is401()
    {
        if (!Available) return;

        using var http = _factory.CreateClient();
        var response = await http.PostAsJsonAsync("api/deals/events", new InterestEventBatchDto(
        [
            Event(Guid.NewGuid().ToString(), InterestActions.Impression, "deal-anon"),
        ]));

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private (HttpClient Http, string Email) Authenticated()
    {
        var email = $"interest-{Guid.NewGuid():N}@test.com";
        var http  = _factory.CreateClient();
        http.DefaultRequestHeaders.Authorization =
            new("Bearer", NotificationE2ETests.BuildJwt($"interest-{Guid.NewGuid():N}", "Viewer", email));
        return (http, email);
    }

    private InterestEventDto Event(string eventId, string action, string entityId) =>
        new(eventId, InterestEntityTypes.Deal, entityId, action, _sessionId, "hot", 0, DateTime.UtcNow);

    public void Dispose()
    {
        _events?.DeleteMany(Builders<BsonDocument>.Filter.Eq("session_id", _sessionId));
        GC.SuppressFinalize(this);
    }
}
