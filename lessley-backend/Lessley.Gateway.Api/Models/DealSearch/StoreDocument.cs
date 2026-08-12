using Lessley.Gateway.Api.Data;
using MongoDB.Bson.Serialization.Attributes;

namespace Lessley.Gateway.Api.Models.DealSearch;

[BsonIgnoreExtraElements]
public class StoreMetadata
{
    // Category names ("GROCERIES"), but legacy rows hold numeric MCCs — see the serializer.
    [BsonElement("mcc_codes")]
    [BsonSerializer(typeof(FlexibleStringListSerializer))]
    public List<string> MccCodes { get; set; } = [];

    [BsonElement("store_url")]
    public string? StoreUrl { get; set; }

    [BsonElement("image_urls")]
    public List<string> ImageUrls { get; set; } = [];
}

/// <summary>
/// A store as the scraping pipeline writes it, in the <c>stores</c> collection.
/// </summary>
/// <remarks>
/// This binds the pipeline's own document, not a projection of it: <c>lessley-deals</c>,
/// <c>deal-optimizer</c>, Personalization and the Gateway all read the same <c>stores</c>
/// rows now.
///
/// The business key lives in one of two places, so <see cref="StoreId"/> resolves both:
/// <c>CanonicalStoreMongoRepository.save</c> pops <c>id</c> into <c>_id</c>, while rows
/// loaded with <c>mongoimport</c> from <c>main/resources/stores.json</c> keep <c>id</c> and
/// get a generated ObjectId <c>_id</c>. Query these by <c>id</c> OR <c>_id</c> for the same
/// reason — see <c>DealFinderRepository.ByBusinessId</c>.
///
/// The JSON property names are unchanged from before that move, so the SPA contract is
/// unaffected: the two raw key fields are <c>[JsonIgnore]</c>d.
/// </remarks>
[BsonIgnoreExtraElements]
public class StoreDocument
{
    [BsonId]
    [BsonSerializer(typeof(FlexibleIdSerializer))]
    [System.Text.Json.Serialization.JsonIgnore]
    public string MongoId { get; set; } = "";

    [BsonElement("id")]
    [System.Text.Json.Serialization.JsonIgnore]
    public string? BusinessId { get; set; }

    /// <summary>The canonical store id, whichever field carries it.</summary>
    [BsonIgnore]
    public string StoreId => string.IsNullOrEmpty(BusinessId) ? MongoId : BusinessId;

    [BsonElement("name")]
    public string Name { get; set; } = "";

    [BsonElement("metadata")]
    public StoreMetadata Metadata { get; set; } = new();
}
