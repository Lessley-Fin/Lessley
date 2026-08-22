using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace Lessley.Gateway.Api.Models.Interest;

/// <summary>
/// The vocabulary of engagement. Anything outside these sets is rejected at the service
/// boundary rather than stored, so the rollup never has to defend against unknown actions.
/// </summary>
public static class InterestActions
{
    public const string Impression = "impression";
    public const string SearchHit  = "search_hit";
    public const string Open       = "open";
    public const string CouponCopy = "coupon_copy";
    public const string Redirect   = "redirect";

    public static readonly IReadOnlySet<string> All =
        new HashSet<string> { Impression, SearchHit, Open, CouponCopy, Redirect };

    /// <summary>
    /// The actions that mean a user *chose* this deal after seeing it. These are the
    /// numerator of the engagement rate; <see cref="Impression"/> is its denominator and
    /// <see cref="SearchHit"/> is neither — a search result the user never scrolled to is
    /// not a choice.
    /// </summary>
    public static readonly IReadOnlySet<string> Engagement =
        new HashSet<string> { Open, CouponCopy, Redirect };
}

public static class InterestEntityTypes
{
    public const string Deal  = "deal";
    public const string Store = "store";

    public static readonly IReadOnlySet<string> All = new HashSet<string> { Deal, Store };
}

/// <summary>
/// One raw engagement event, as the client reports it, in the <c>interest_events</c> collection.
/// </summary>
/// <remarks>
/// Raw events are never read by a request path — they exist only to be collapsed by the
/// nightly rollup into <see cref="EntityStats"/>. The TTL on <c>ts</c> is therefore both the
/// retention policy and the scoring window: an event past it has no remaining purpose.
///
/// <see cref="EventId"/> is a client-generated UUID with a unique index behind it, which is
/// what makes a retried flush idempotent. <see cref="UserId"/> is always overwritten from the
/// caller's JWT — a value in the request body is ignored.
/// </remarks>
[BsonIgnoreExtraElements]
public class InterestEvent
{
    [BsonId]
    public ObjectId Id { get; set; }

    [BsonElement("event_id")]
    public string EventId { get; set; } = "";

    /// <summary>"deal" | "store" — see <see cref="InterestEntityTypes"/>.</summary>
    [BsonElement("entity_type")]
    public string EntityType { get; set; } = "";

    [BsonElement("entity_id")]
    public string EntityId { get; set; } = "";

    /// <summary>See <see cref="InterestActions"/>.</summary>
    [BsonElement("action")]
    public string Action { get; set; } = "";

    /// <summary>The caller's email, taken from the JWT. Never trusted from the body.</summary>
    [BsonElement("user_id")]
    public string UserId { get; set; } = "";

    /// <summary>Per-tab UUID. Lets a session be reconstructed without joining on the user.</summary>
    [BsonElement("session_id")]
    public string SessionId { get; set; } = "";

    /// <summary>Which screen the event came from, e.g. "hot" or "deal_finder".</summary>
    [BsonElement("surface")]
    public string Surface { get; set; } = "";

    /// <summary>
    /// 0-based rank in the list the event came from. Logged from day one purely so position
    /// debiasing can be switched on later without a backfill — nothing reads it yet.
    /// </summary>
    [BsonElement("position")]
    public int? Position { get; set; }

    [BsonElement("ts")]
    public DateTime Ts { get; set; }
}

/// <summary>
/// The rollup's output: one scored row per entity, in <c>entity_stats</c>.
/// </summary>
[BsonIgnoreExtraElements]
public class EntityStats
{
    [BsonId]
    public ObjectId Id { get; set; }

    [BsonElement("entity_type")]
    public string EntityType { get; set; } = "";

    [BsonElement("entity_id")]
    public string EntityId { get; set; } = "";

    [BsonElement("hot_score")]
    public double HotScore { get; set; }

    /// <summary>Distinct users who saw it — the rate's denominator, not an event count.</summary>
    [BsonElement("impressions")]
    public int Impressions { get; set; }

    /// <summary>Distinct users who did anything at all with it.</summary>
    [BsonElement("actors")]
    public int Actors { get; set; }

    /// <summary>End of the window this row was scored over.</summary>
    [BsonElement("window_end")]
    public DateTime WindowEnd { get; set; }
}

/// <summary>
/// A search that returned nothing, in <c>search_gaps</c> — a demand-ranked list of what the
/// catalog does not carry.
/// </summary>
/// <remarks>
/// Deliberately carries no <c>user_id</c>. Free-text search over a fintech user base is
/// sensitive by nature, and a gap list is just as useful in aggregate; storing it unjoinable
/// to an identity is what keeps it safe to keep indefinitely.
/// </remarks>
[BsonIgnoreExtraElements]
public class SearchGap
{
    [BsonId]
    public ObjectId Id { get; set; }

    [BsonElement("query_norm")]
    public string QueryNorm { get; set; } = "";

    [BsonElement("hits")]
    public long Hits { get; set; }

    [BsonElement("last_seen")]
    public DateTime LastSeen { get; set; }
}
