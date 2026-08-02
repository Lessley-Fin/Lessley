using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace Lessley.Gateway.Api.Models.DealSearch;

[BsonIgnoreExtraElements]
public class StoreMetadata
{
    [BsonElement("mcc_codes")]
    public List<string> MccCodes { get; set; } = [];

    [BsonElement("store_url")]
    public string? StoreUrl { get; set; }

    [BsonElement("image_urls")]
    public List<string> ImageUrls { get; set; } = [];
}

[BsonIgnoreExtraElements]
public class StoreDocument
{
    [BsonId]
    public ObjectId MongoId { get; set; }

    [BsonElement("id")]
    public string StoreId { get; set; } = "";

    [BsonElement("name")]
    public string Name { get; set; } = "";

    [BsonElement("metadata")]
    public StoreMetadata Metadata { get; set; } = new();
}
