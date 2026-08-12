using Lessley.Gateway.Api.Models.DealSearch;
using Lessley.Gateway.Api.Services.Interfaces;
using MongoDB.Bson;
using MongoDB.Driver;
using System.Text.RegularExpressions;

namespace Lessley.Gateway.Api.Services.Classes;

public class DealFinderRepository : IDealFinderRepository
{
    private readonly IMongoCollection<StoreDocument> _storeCollection;
    private readonly IMongoCollection<DealDocument>  _dealCollection;

    public DealFinderRepository(IMongoClient client)
    {
        // The scraping pipeline's own collections — the same ones deal-optimizer and
        // Personalization read. There is no longer a projected read model in between.
        var db           = client.GetDatabase("lessley");
        _storeCollection = db.GetCollection<StoreDocument>("stores");
        _dealCollection  = db.GetCollection<DealDocument>("deals");
    }

    /// <summary>
    /// Matches a business key in either of the two places it can live: <c>id</c> on rows
    /// imported from <c>main/resources/*.json</c> (whose <c>_id</c> is a generated ObjectId),
    /// or <c>_id</c> on rows the pipeline wrote. Both shapes occur in live databases, so a
    /// lookup that checks only one silently finds nothing.
    /// </summary>
    private static FilterDefinition<T> ByBusinessId<T>(string id) =>
        Builders<T>.Filter.Or(
            Builders<T>.Filter.Eq("id", id),
            Builders<T>.Filter.Eq("_id", id));

    public async Task<DealSearchResult?> GetByIdAsync(string dealId, CancellationToken ct = default)
    {
        var deal = await _dealCollection
            .Find(ByBusinessId<DealDocument>(dealId))
            .FirstOrDefaultAsync(ct);

        if (deal is null) return null;

        var store = await _storeCollection
            .Find(ByBusinessId<StoreDocument>(deal.StoreId))
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
            storeFilter &= Builders<StoreDocument>.Filter.Regex(s => s.Name, LiteralContains(query.StoreText));

        var matchingStores = await _storeCollection.Find(storeFilter).ToListAsync(ct);

        if (matchingStores.Count == 0)
            return ([], 0);

        var storeById = matchingStores.ToDictionary(s => s.StoreId);
        var storeIds  = matchingStores.Select(s => s.StoreId).ToList();

        // Step 2: filter deals within matching stores
        var dealFilter = Builders<DealDocument>.Filter.In(d => d.StoreId, storeIds);

        if (!string.IsNullOrWhiteSpace(query.DealText))
            dealFilter &= Builders<DealDocument>.Filter.Or(
                Builders<DealDocument>.Filter.Regex(d => d.Title,       LiteralContains(query.DealText)),
                Builders<DealDocument>.Filter.Regex(d => d.Description, LiteralContains(query.DealText))
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

    // Escape user input so it is matched as a literal substring. Prevents regex injection
    // and catastrophic-backtracking (ReDoS) from attacker-supplied patterns.
    private static BsonRegularExpression LiteralContains(string text) =>
        new(Regex.Escape(text), "i");
}
