using Lessley.Gateway.Api.Models.DealSearch;
using Lessley.Gateway.Api.Services.Interfaces;
using MongoDB.Bson;
using MongoDB.Driver;

namespace Lessley.Gateway.Api.Services.Classes;

public class DealFinderRepository : IDealFinderRepository
{
    private readonly IMongoCollection<StoreDocument> _storeCollection;
    private readonly IMongoCollection<DealDocument>  _dealCollection;

    public DealFinderRepository(IMongoClient client)
    {
        var db           = client.GetDatabase("lessley");
        _storeCollection = db.GetCollection<StoreDocument>("store_list");
        _dealCollection  = db.GetCollection<DealDocument>("deal_list");
    }

    public async Task<DealSearchResult?> GetByIdAsync(string dealId, CancellationToken ct = default)
    {
        var deal = await _dealCollection
            .Find(d => d.DealId == dealId)
            .FirstOrDefaultAsync(ct);

        if (deal is null) return null;

        var store = await _storeCollection
            .Find(s => s.StoreId == deal.StoreId)
            .FirstOrDefaultAsync(ct);

        if (store is null) return null;

        return new DealSearchResult(deal, store);
    }

    public async Task<(List<DealSearchResult> Results, int Total)> SearchAsync(DealSearchQuery query, CancellationToken ct = default)
    {
        // Step 1: filter stores
        var storeFilter = Builders<StoreDocument>.Filter.Empty;

        if (query.MccCodes?.Count > 0)
            storeFilter &= Builders<StoreDocument>.Filter.AnyIn(s => s.Metadata.MccCodes, query.MccCodes);

        if (!string.IsNullOrWhiteSpace(query.StoreText))
            storeFilter &= Builders<StoreDocument>.Filter.Regex(s => s.Name, new BsonRegularExpression(query.StoreText, "i"));

        var matchingStores = await _storeCollection.Find(storeFilter).ToListAsync(ct);

        if (matchingStores.Count == 0)
            return ([], 0);

        var storeById = matchingStores.ToDictionary(s => s.StoreId);
        var storeIds  = matchingStores.Select(s => s.StoreId).ToList();

        // Step 2: filter deals within matching stores
        var dealFilter = Builders<DealDocument>.Filter.In(d => d.StoreId, storeIds);

        if (!string.IsNullOrWhiteSpace(query.DealText))
            dealFilter &= Builders<DealDocument>.Filter.Or(
                Builders<DealDocument>.Filter.Regex(d => d.Title,       new BsonRegularExpression(query.DealText, "i")),
                Builders<DealDocument>.Filter.Regex(d => d.Description, new BsonRegularExpression(query.DealText, "i"))
            );

        var total = (int)await _dealCollection.CountDocumentsAsync(dealFilter, cancellationToken: ct);

        var deals = await _dealCollection.Find(dealFilter)
            .Skip((query.Page - 1) * query.PageSize)
            .Limit(query.PageSize)
            .ToListAsync(ct);

        // Step 3: populate store reference
        var results = deals
            .Where(d => storeById.ContainsKey(d.StoreId))
            .Select(d => new DealSearchResult(d, storeById[d.StoreId]))
            .ToList();

        return (results, total);
    }
}
