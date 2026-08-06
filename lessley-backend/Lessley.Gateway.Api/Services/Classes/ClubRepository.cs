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
        _collection = client.GetDatabase("lessley").GetCollection<BsonDocument>("club_list");
    }

    public async Task<List<ClubDto>> GetClubsAsync(CancellationToken ct = default)
    {
        var projection = Builders<BsonDocument>.Projection.Include("id").Include("name").Exclude("_id");

        var docs = await _collection
            .Find(FilterDefinition<BsonDocument>.Empty)
            .Project(projection)
            .ToListAsync(ct);

        return docs
            .Select(d => new ClubDto(d["id"].AsString, d["name"].AsString))
            .ToList();
    }
}
