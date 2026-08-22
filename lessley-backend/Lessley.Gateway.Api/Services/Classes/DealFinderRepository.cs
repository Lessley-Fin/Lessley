using Lessley.Gateway.Api.Models.DealSearch;
using Lessley.Gateway.Api.Services.Interfaces;
using MongoDB.Bson;
using MongoDB.Bson.Serialization;
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

    public async Task<List<DealSearchResult>> GetByIdsAsync(IReadOnlyList<string> dealIds, CancellationToken ct = default)
    {
        if (dealIds.Count == 0) return [];

        var deals = await _dealCollection.Find(ByBusinessIds<DealDocument>(dealIds)).ToListAsync(ct);

        // Mongo returns matches in storage order; the caller's order is the ranking, so
        // restore it here rather than making every caller re-sort.
        var rank    = dealIds.Select((id, i) => (id, i)).ToDictionary(p => p.id, p => p.i);
        var ordered = deals
            .Where(d => rank.ContainsKey(d.DealId))
            .OrderBy(d => rank[d.DealId])
            .ToList();

        return await WithStoresAsync(ordered, ct);
    }

    public async Task<List<DealSearchResult>> RecentlyScrapedAsync(
        int limit, IReadOnlyCollection<string> excluding, CancellationToken ct = default)
    {
        if (limit <= 0) return [];

        var deals = await _dealCollection
            .Find(NotIn<DealDocument>(excluding))
            .Sort(Builders<DealDocument>.Sort.Descending("scraped_at"))
            // Over-fetch: a deal whose store row is missing is dropped by the join below,
            // and a short hot list is more visible than a slightly wasteful query.
            .Limit(limit * 2)
            .ToListAsync(ct);

        var results = await WithStoresAsync(deals, ct);
        return results.Take(limit).ToList();
    }

    public async Task<List<DealSearchResult>> RandomDealsAsync(
        int limit, DateTime scrapedAfter, IReadOnlyCollection<string> excluding, CancellationToken ct = default)
    {
        if (limit <= 0) return [];

        var match = NotIn<DealDocument>(excluding) & ScrapedSince<DealDocument>(scrapedAfter);

        var pipeline = new BsonDocument[]
        {
            new("$match",  match.Render(new RenderArgs<DealDocument>(
                BsonSerializer.SerializerRegistry.GetSerializer<DealDocument>(),
                BsonSerializer.SerializerRegistry))),
            new("$sample", new BsonDocument("size", limit * 2)),
        };

        var deals   = await _dealCollection.Aggregate<DealDocument>(pipeline, cancellationToken: ct).ToListAsync(ct);
        var results = await WithStoresAsync(deals, ct);
        return results.Take(limit).ToList();
    }

    // Both key fields only — the business id lives in one or the other, and nothing else on
    // the document is needed to prune orphaned stats.
    public async Task<List<string>> AllDealIdsAsync(CancellationToken ct = default) =>
        (await _dealCollection.Find(Builders<DealDocument>.Filter.Empty)
            .Project<DealDocument>(Builders<DealDocument>.Projection.Include("id"))
            .ToListAsync(ct))
        .Select(d => d.DealId)
        .Where(id => !string.IsNullOrEmpty(id))
        .ToList();

    public async Task<List<string>> AllStoreIdsAsync(CancellationToken ct = default) =>
        (await _storeCollection.Find(Builders<StoreDocument>.Filter.Empty)
            .Project<StoreDocument>(Builders<StoreDocument>.Projection.Include("id"))
            .ToListAsync(ct))
        .Select(s => s.StoreId)
        .Where(id => !string.IsNullOrEmpty(id))
        .ToList();

    /// <summary>
    /// Attaches each deal's store, dropping deals whose store row is missing — the same join
    /// step <see cref="SearchAsync"/> does, shared so every read path returns the same shape.
    /// </summary>
    private async Task<List<DealSearchResult>> WithStoresAsync(List<DealDocument> deals, CancellationToken ct)
    {
        if (deals.Count == 0) return [];

        var storeIds = deals.Select(d => d.StoreId).Distinct().ToList();
        var stores   = await _storeCollection.Find(ByBusinessIds<StoreDocument>(storeIds)).ToListAsync(ct);

        var storeById = stores
            .GroupBy(s => s.StoreId)
            .ToDictionary(g => g.Key, g => g.First());

        return deals
            .Where(d => storeById.ContainsKey(d.StoreId))
            .Select(d => new DealSearchResult(d, storeById[d.StoreId]))
            .ToList();
    }

    /// <summary>Plural <see cref="ByBusinessId{T}"/> — matches on either key field.</summary>
    private static FilterDefinition<T> ByBusinessIds<T>(IReadOnlyCollection<string> ids) =>
        Builders<T>.Filter.Or(
            Builders<T>.Filter.In<string>("id",  ids),
            Builders<T>.Filter.In<string>("_id", ids));

    /// <summary>Excludes ids under either key field. Matches everything when the set is empty.</summary>
    private static FilterDefinition<T> NotIn<T>(IReadOnlyCollection<string> ids) =>
        ids.Count == 0 ? Builders<T>.Filter.Empty : Builders<T>.Filter.Not(ByBusinessIds<T>(ids));

    /// <summary>
    /// <c>scraped_at</c> at or after a cutoff, in both stored shapes.
    /// </summary>
    /// <remarks>
    /// The pipeline writes ISO-8601 strings and imports write BSON dates (see
    /// <c>FlexibleDateTimeSerializer</c>). BSON never compares across types, so a single
    /// <c>$gte</c> against a date silently excludes every scraped row. The string branch
    /// relies on ISO-8601 being lexicographically ordered, which is exactly why the pipeline
    /// emits that format.
    /// </remarks>
    private static FilterDefinition<T> ScrapedSince<T>(DateTime cutoff) =>
        Builders<T>.Filter.Or(
            new BsonDocument("scraped_at", new BsonDocument("$gte", cutoff.ToUniversalTime())),
            new BsonDocument("scraped_at", new BsonDocument("$gte",
                cutoff.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss"))));

    // Escape user input so it is matched as a literal substring. Prevents regex injection
    // and catastrophic-backtracking (ReDoS) from attacker-supplied patterns.
    private static BsonRegularExpression LiteralContains(string text) =>
        new(Regex.Escape(text), "i");
}
