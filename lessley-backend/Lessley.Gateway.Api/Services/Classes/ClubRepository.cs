using Lessley.Gateway.Api.Models.Club;
using Lessley.Gateway.Api.Services.Interfaces;
using MongoDB.Bson;
using MongoDB.Driver;

namespace Lessley.Gateway.Api.Services.Classes;

public class ClubRepository : IClubRepository
{
    private readonly IMongoCollection<BsonDocument> _collection;

    public ClubRepository(IMongoClient client)
    {
        // The pipeline's own collection, shared with Personalization and the scraper.
        _collection = client.GetDatabase("lessley").GetCollection<BsonDocument>("clubs");
    }

    public async Task<List<ClubDto>> GetClubsAsync(CancellationToken ct = default)
    {
        // The business key lives in one of two places, so both are projected: rows the
        // pipeline seeds put it in _id ("club_hot"), while rows imported from
        // main/resources/clubs.json keep it in `id` and get a generated ObjectId _id.
        // Reading only _id throws InvalidCastException on the imported shape.
        var projection = Builders<BsonDocument>.Projection.Include("_id").Include("id").Include("name");

        var docs = await _collection
            .Find(FilterDefinition<BsonDocument>.Empty)
            .Project(projection)
            .ToListAsync(ct);

        return docs
            .Select(d => new ClubDto(BusinessId(d), d.GetValue("name", "").AsString))
            .ToList();
    }

    /// <summary>The club's business id, from <c>id</c> when present and <c>_id</c> otherwise.</summary>
    private static string BusinessId(BsonDocument doc)
    {
        var id = doc.GetValue("id", BsonNull.Value);
        if (id.IsString && !string.IsNullOrEmpty(id.AsString)) return id.AsString;

        var mongoId = doc.GetValue("_id", BsonNull.Value);
        return mongoId.IsBsonNull ? "" : mongoId.ToString()!;
    }
}
