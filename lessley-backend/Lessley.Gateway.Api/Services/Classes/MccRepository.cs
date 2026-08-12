using Lessley.Gateway.Api.Models.Mcc;
using Lessley.Gateway.Api.Services.Interfaces;
using MongoDB.Bson;
using MongoDB.Driver;

namespace Lessley.Gateway.Api.Services.Classes;

public class MccRepository : IMccRepository
{
    private readonly IMongoCollection<BsonDocument> _collection;

    public MccRepository(IMongoClient client)
    {
        _collection = client.GetDatabase("lessley").GetCollection<BsonDocument>("mccs");
    }

    public async Task<List<MccCategoryDto>> GetCategoriesAsync(CancellationToken ct = default)
    {
        var pipeline = new[]
        {
            new BsonDocument("$group", new BsonDocument("_id", "$category")),
            new BsonDocument("$sort", new BsonDocument("_id", 1)),
            new BsonDocument("$project", new BsonDocument
            {
                { "_id", 0 },
                { "category", "$_id" },
            }),
        };

        var results = await _collection
            .Aggregate<BsonDocument>(pipeline, cancellationToken: ct)
            .ToListAsync(ct);

        return results
            .Select(doc => new MccCategoryDto(doc["category"].AsString))
            .ToList();
    }
}
