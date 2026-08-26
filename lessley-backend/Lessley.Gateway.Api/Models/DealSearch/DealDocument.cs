using Lessley.Gateway.Api.Data;
using MongoDB.Bson.Serialization.Attributes;

namespace Lessley.Gateway.Api.Models.DealSearch;

/// <summary>
/// A deal as the scraping pipeline writes it, in the <c>deals</c> collection.
/// </summary>
/// <remarks>
/// Reads the pipeline's own document rather than a flattened projection of it, so the
/// scraper, <c>deal-optimizer</c>, Personalization and the Gateway all share one shape.
/// Two consequences, both handled here rather than by changing the data:
///
/// * the business key is <c>_id</c> on rows <c>DealMongoRepository.save</c> wrote, but
///   <c>id</c> (with an ObjectId <c>_id</c>) on rows imported from
///   <c>main/resources/deals.json</c> — <see cref="DealId"/> resolves either;
/// * timestamps are ISO strings, which is what <see cref="FlexibleDateTimeSerializer"/> is for.
///
/// The display fields a client renders — discount, limits, redemption channels, membership —
/// live nested under <c>discount_logic</c>/<c>constraints</c> in the stored document. The
/// computed properties below flatten them into the shape the SPA consumes, so a client never
/// has to re-derive what a deal is worth from the raw sub-documents.
/// </remarks>
[BsonIgnoreExtraElements]
public class DealDocument
{
    [BsonId]
    [BsonSerializer(typeof(FlexibleIdSerializer))]
    [System.Text.Json.Serialization.JsonIgnore]
    public string MongoId { get; set; } = "";

    [BsonElement("id")]
    [System.Text.Json.Serialization.JsonIgnore]
    public string? BusinessId { get; set; }

    /// <summary>The canonical deal id, whichever field carries it.</summary>
    [BsonIgnore]
    public string DealId => string.IsNullOrEmpty(BusinessId) ? MongoId : BusinessId;

    [BsonElement("store_id")]
    public string StoreId { get; set; } = "";

    [BsonElement("title")]
    public string Title { get; set; } = "";

    [BsonElement("deal_description")]
    public string? Description { get; set; }

    // Filled by the pipeline's PersistStage from source_id; rows written before that map
    // existed can still be null, which `deals backfill-club-ids` repairs.
    [BsonElement("club_id")]
    public string? ClubId { get; set; }

    [BsonElement("scraped_at")]
    [BsonSerializer(typeof(FlexibleDateTimeSerializer))]
    public DateTime ScrapedAt { get; set; }

    [BsonElement("resolved_at")]
    [BsonSerializer(typeof(FlexibleNullableDateTimeSerializer))]
    public DateTime? ResolvedAt { get; set; }

    [BsonElement("benefit_url")]
    public string? BenefitUrl { get; set; }

    [BsonElement("url")]
    public string? Url { get; set; }

    [BsonElement("coupon_code")]
    public string? CouponCode { get; set; }

    [BsonElement("deal_type")]
    public string? DealType { get; set; }

    /// <summary>
    /// <c>"active"</c> or <c>"expired"</c>, stamped by the scraping pipeline's versioning
    /// layer after every run. Null on rows written before it existed.
    /// </summary>
    [BsonElement("status")]
    [System.Text.Json.Serialization.JsonIgnore]
    public string? Status { get; set; }

    /// <summary>
    /// Whether the source has stopped offering this deal. Search filters expired deals out,
    /// but a lookup by id still returns one so a saved deal reads as "this offer ended"
    /// rather than vanishing — hence the flag on the response.
    /// <para>Null means the row predates the field, i.e. still on offer as far as anyone knew.</para>
    /// </summary>
    [BsonIgnore]
    public bool IsExpired => Status == "expired";

    /// <summary>When the pipeline concluded the deal was gone. Null while it is on offer.</summary>
    [BsonElement("expired_at")]
    [BsonSerializer(typeof(FlexibleNullableDateTimeSerializer))]
    public DateTime? ExpiredAt { get; set; }

    [BsonElement("currency")]
    public string? Currency { get; set; }

    [BsonElement("terms_and_conditions")]
    public string? TermsAndConditions { get; set; }

    // Both raw sub-documents are [JsonIgnore]d: the client contract is the flattened view
    // below. Keeping them out of the response also keeps System.Text.Json away from their
    // BsonValue members, whose As* accessors throw when the stored type is not the one
    // being asked for — that failure took down every deal search once.

    /// <summary>Raw offer terms; <see cref="Discount"/> is what a client renders.</summary>
    [BsonElement("discount_logic")]
    [System.Text.Json.Serialization.JsonIgnore]
    public DiscountLogic? DiscountLogic { get; set; }

    /// <summary>Raw parsed terms; <see cref="Limits"/> and friends are the rendered view.</summary>
    [BsonElement("constraints")]
    [System.Text.Json.Serialization.JsonIgnore]
    public DealConstraints? Constraints { get; set; }

    // ── Rendered view of the nested documents above ──────────────────────────────
    // [BsonIgnore] keeps them off any write path; System.Text.Json still emits them.

    /// <summary>What the deal is worth, split by reward type so a badge can tell them apart.</summary>
    [BsonIgnore]
    public DealDiscount Discount => DealDiscount.From(DiscountLogic);

    /// <summary>Caps a client shows as benefit terms.</summary>
    [BsonIgnore]
    public DealLimits Limits => DealLimits.From(Constraints);

    /// <summary>Channels the deal can be redeemed through, e.g. ["website"].</summary>
    [BsonIgnore]
    public List<string> RedeemChannels => Constraints?.RedemptionChannelNames() ?? [];

    /// <summary>Tri-state on disk (true / "yes" / absent) reduced to a bool or null.</summary>
    [BsonIgnore]
    public bool? MembershipRequired => Constraints?.Eligibility?.MembershipRequiredFlag;
}

// ── Nested pipeline sub-documents ────────────────────────────────────────────────

[BsonIgnoreExtraElements]
public class DiscountLogic
{
    [BsonElement("reward")]
    public DiscountReward? Reward { get; set; }

    [BsonElement("condition")]
    public DiscountCondition? Condition { get; set; }
}

[BsonIgnoreExtraElements]
public class DiscountReward
{
    /// <summary>percentage_off | fixed_discount_amount | fixed_total_amount.</summary>
    [BsonElement("type")]
    public string? Type { get; set; }

    [BsonElement("value")]
    public double? Value { get; set; }

    [BsonElement("max_discount_amount")]
    public double? MaxDiscountAmount { get; set; }
}

[BsonIgnoreExtraElements]
public class DiscountCondition
{
    /// <summary>min_spend | exact_spend | min_quantity.</summary>
    [BsonElement("type")]
    public string? Type { get; set; }

    [BsonElement("value")]
    public double? Value { get; set; }
}

[BsonIgnoreExtraElements]
public class DealConstraints
{
    [BsonElement("limits")]
    public ConstraintLimits? Limits { get; set; }

    [BsonElement("eligibility")]
    public ConstraintEligibility? Eligibility { get; set; }

    /// <summary>
    /// Either {"website": "yes", ...} or a bare list of channel names — the parser has
    /// emitted both shapes, so both are read. Never serialized: see DealDocument.
    /// </summary>
    [BsonElement("redemption_channels")]
    [System.Text.Json.Serialization.JsonIgnore]
    public MongoDB.Bson.BsonValue? RedemptionChannels { get; set; }

    /// <summary>The channels marked available, in the order they appear.</summary>
    public List<string> RedemptionChannelNames()
    {
        if (RedemptionChannels is null || RedemptionChannels.IsBsonNull) return [];

        if (RedemptionChannels is MongoDB.Bson.BsonArray array)
            return array.Where(v => !v.IsBsonNull).Select(v => v.ToString()!).ToList();

        if (RedemptionChannels is MongoDB.Bson.BsonDocument document)
            return document.Elements
                .Where(e => IsAvailable(e.Value))
                .Select(e => e.Name)
                .ToList();

        return [];
    }

    // "yes" / true / 1 all mean the channel is available; anything else does not.
    private static bool IsAvailable(MongoDB.Bson.BsonValue value) => value.BsonType switch
    {
        MongoDB.Bson.BsonType.Boolean => value.AsBoolean,
        MongoDB.Bson.BsonType.Int32   => value.AsInt32 == 1,
        MongoDB.Bson.BsonType.Int64   => value.AsInt64 == 1,
        MongoDB.Bson.BsonType.String  => value.AsString.Equals("yes", StringComparison.OrdinalIgnoreCase)
                                      || value.AsString.Equals("true", StringComparison.OrdinalIgnoreCase),
        _ => false,
    };
}

[BsonIgnoreExtraElements]
public class ConstraintLimits
{
    [BsonElement("minimum_purchase")]
    public double? MinimumPurchase { get; set; }

    [BsonElement("max_uses_per_transaction")]
    public int? MaxUsesPerTransaction { get; set; }

    [BsonElement("max_uses_per_month")]
    public int? MaxUsesPerMonth { get; set; }
}

[BsonIgnoreExtraElements]
public class ConstraintEligibility
{
    /// <summary>Written as a bool by the parser, but "yes"/"no" by older rows.</summary>
    [BsonElement("membership_required")]
    [System.Text.Json.Serialization.JsonIgnore]
    public MongoDB.Bson.BsonValue? MembershipRequired { get; set; }

    public bool? MembershipRequiredFlag => MembershipRequired switch
    {
        null                                              => null,
        var v when v.IsBsonNull                           => null,
        var v when v.BsonType == MongoDB.Bson.BsonType.Boolean => v.AsBoolean,
        var v when v.BsonType == MongoDB.Bson.BsonType.String  => v.AsString.Equals("yes", StringComparison.OrdinalIgnoreCase),
        _                                                 => null,
    };
}

// ── Client-facing shapes ─────────────────────────────────────────────────────────

/// <summary>
/// What the deal is worth. The raw <c>discount_logic</c> carries the amount's meaning in
/// <c>reward.type</c>, so it is split by reward type here: a ratio off (<c>PercentOff</c>
/// 0.3 = 30%), ILS off, or a price paid instead.
/// </summary>
public class DealDiscount
{
    public string? RewardType { get; init; }
    public double? PercentOff { get; init; }
    public double? AmountOff { get; init; }
    public double? FixedPrice { get; init; }
    public double? MaxDiscountAmount { get; init; }
    public string? ConditionType { get; init; }
    public double? MinSpend { get; init; }
    public double? MinQuantity { get; init; }

    public static DealDiscount From(DiscountLogic? logic)
    {
        var rewardType    = logic?.Reward?.Type;
        var rewardValue   = logic?.Reward?.Value;
        var conditionType = logic?.Condition?.Type;
        var conditionValue = logic?.Condition?.Value;

        return new DealDiscount
        {
            RewardType        = rewardType,
            PercentOff        = rewardType == "percentage_off" ? rewardValue : null,
            AmountOff         = rewardType == "fixed_discount_amount" ? rewardValue : null,
            FixedPrice        = rewardType == "fixed_total_amount" ? rewardValue : null,
            MaxDiscountAmount = logic?.Reward?.MaxDiscountAmount,
            ConditionType     = conditionType,
            MinSpend          = conditionType is "min_spend" or "exact_spend" ? conditionValue : null,
            MinQuantity       = conditionType == "min_quantity" ? conditionValue : null,
        };
    }
}

/// <summary>Caps a client shows as benefit terms.</summary>
public class DealLimits
{
    public double? MinimumPurchase { get; init; }
    public int? MaxUsesPerTransaction { get; init; }
    public int? MaxUsesPerMonth { get; init; }

    public static DealLimits From(DealConstraints? constraints) => new()
    {
        MinimumPurchase       = constraints?.Limits?.MinimumPurchase,
        MaxUsesPerTransaction = constraints?.Limits?.MaxUsesPerTransaction,
        MaxUsesPerMonth       = constraints?.Limits?.MaxUsesPerMonth,
    };
}
