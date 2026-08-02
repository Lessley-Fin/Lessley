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
}
