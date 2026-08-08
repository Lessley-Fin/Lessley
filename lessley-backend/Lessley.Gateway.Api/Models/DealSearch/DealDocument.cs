using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace Lessley.Gateway.Api.Models.DealSearch;

[BsonIgnoreExtraElements]
public class DealDocument
{
    [BsonId]
    public ObjectId MongoId { get; set; }

    [BsonElement("id")]
    public string DealId { get; set; } = "";

    [BsonElement("store_id")]
    public string StoreId { get; set; } = "";

    [BsonElement("title")]
    public string Title { get; set; } = "";

    [BsonElement("deal_description")]
    public string? Description { get; set; }

    [BsonElement("club_id")]
    public string ClubId { get; set; } = "";

    [BsonElement("scraped_at")]
    public DateTime ScrapedAt { get; set; }

    [BsonElement("resolved_at")]
    public DateTime? ResolvedAt { get; set; }

    [BsonElement("benefit_url")]
    public string? BenefitUrl { get; set; }

    [BsonElement("url")]
    public string? Url { get; set; }

    [BsonElement("redeem_channels")]
    public List<string> RedeemChannels { get; set; } = [];

    [BsonElement("coupon_code")]
    public string? CouponCode { get; set; }

    [BsonElement("deal_type")]
    public string? DealType { get; set; }

    [BsonElement("currency")]
    public string? Currency { get; set; }

    [BsonElement("terms_and_conditions")]
    public string? TermsAndConditions { get; set; }

    [BsonElement("discount")]
    public DealDiscount? Discount { get; set; }

    [BsonElement("limits")]
    public DealLimits? Limits { get; set; }

    [BsonElement("membership_required")]
    public bool? MembershipRequired { get; set; }
}

/// <summary>
/// What the deal is worth. The pipeline splits the raw <c>discount_logic</c> by
/// reward type, so exactly one of the three value fields is set: a ratio off
/// (<c>PercentOff</c> 0.3 = 30%), ILS off, or a price paid instead.
/// </summary>
[BsonIgnoreExtraElements]
public class DealDiscount
{
    [BsonElement("reward_type")]
    public string? RewardType { get; set; }

    [BsonElement("percent_off")]
    public double? PercentOff { get; set; }

    [BsonElement("amount_off")]
    public double? AmountOff { get; set; }

    [BsonElement("fixed_price")]
    public double? FixedPrice { get; set; }

    [BsonElement("max_discount_amount")]
    public double? MaxDiscountAmount { get; set; }

    [BsonElement("condition_type")]
    public string? ConditionType { get; set; }

    [BsonElement("min_spend")]
    public double? MinSpend { get; set; }

    [BsonElement("min_quantity")]
    public double? MinQuantity { get; set; }
}

/// <summary>Caps a client shows as benefit terms.</summary>
[BsonIgnoreExtraElements]
public class DealLimits
{
    [BsonElement("minimum_purchase")]
    public double? MinimumPurchase { get; set; }

    [BsonElement("max_uses_per_transaction")]
    public int? MaxUsesPerTransaction { get; set; }

    [BsonElement("max_uses_per_month")]
    public int? MaxUsesPerMonth { get; set; }
}
