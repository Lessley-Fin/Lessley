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

    /// <summary>
    /// Excludes deals the scraping pipeline has marked as no longer offered. Its versioning
    /// layer stamps every row <c>status: "active"</c> or <c>"expired"</c> after each run;
    /// without this filter, search keeps returning offers the source took down months ago.
    /// <para>
    /// Written as "not expired" rather than "is active" deliberately: rows written before
    /// the pipeline stamped a status carry no such field, and they are live deals that
    /// simply predate it — matching only <c>"active"</c> would hide all of them.
    /// </para>
    /// </summary>
    private static FilterDefinition<DealDocument> NotExpired() =>
        Builders<DealDocument>.Filter.Ne("status", "expired");

    public async Task<DealSearchResult?> GetByIdAsync(string dealId, CancellationToken ct = default)
    {
        // Fetched by explicit id, so an expired deal is still returned here: a saved deal
        // or a notification linking to one must resolve to "this offer ended", not a 404.
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
        var dealFilter = Builders<DealDocument>.Filter.In(d => d.StoreId, storeIds) & NotExpired();

        // Scoped by the service to the caller's own clubs. Matched on the raw field name
        // because `club_id` is nullable on the document: a row the pipeline wrote before
        // the club map existed carries none, and cannot be attributed to any club, so it
        // is correctly excluded here rather than leaking into every user's results.
        if (query.ClubIds?.Count > 0)
            dealFilter &= Builders<DealDocument>.Filter.In("club_id", query.ClubIds);

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
