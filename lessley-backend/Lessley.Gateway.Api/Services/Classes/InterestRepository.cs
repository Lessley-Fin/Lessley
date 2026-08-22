using Lessley.Gateway.Api.Models.Interest;
using Lessley.Gateway.Api.Services.Interfaces;
using MongoDB.Bson;
using MongoDB.Driver;

namespace Lessley.Gateway.Api.Services.Classes;

public class InterestRepository : IInterestRepository
{
    private const int MongoDuplicateKey = 11000;

    private readonly IMongoCollection<InterestEvent> _events;
    private readonly IMongoCollection<EntityStats>   _stats;
    private readonly IMongoCollection<SearchGap>     _gaps;

    public InterestRepository(IMongoClient client)
    {
        var db  = client.GetDatabase("lessley");
        _events = db.GetCollection<InterestEvent>("interest_events");
        _stats  = db.GetCollection<EntityStats>("entity_stats");
        _gaps   = db.GetCollection<SearchGap>("search_gaps");
    }

    public async Task<int> InsertManyIgnoringDuplicatesAsync(
        IReadOnlyList<InterestEvent> events, CancellationToken ct = default)
    {
        if (events.Count == 0) return 0;

        try
        {
            // Unordered so one duplicate does not abandon the rest of the batch: every event
            // whose id is new still lands, and the write errors name only the ones that did not.
            await _events.InsertManyAsync(events, new InsertManyOptions { IsOrdered = false }, ct);
            return events.Count;
        }
        catch (MongoBulkWriteException ex) when (ex.WriteErrors.All(e => e.Code == MongoDuplicateKey))
        {
            // A retried flush. The unique index on event_id is what makes this safe to swallow —
            // the only rows rejected are ones already stored.
            return events.Count - ex.WriteErrors.Count;
        }
    }

    // query_norm is not set explicitly: an upsert seeds the new document from the filter's
    // equality conditions, so naming it again in $setOnInsert would only risk a path conflict.
    public Task UpsertSearchGapAsync(string queryNorm, CancellationToken ct = default) =>
        _gaps.UpdateOneAsync(
            Builders<SearchGap>.Filter.Eq(g => g.QueryNorm, queryNorm),
            Builders<SearchGap>.Update
                .Inc(g => g.Hits, 1L)
                .Set(g => g.LastSeen, DateTime.UtcNow),
            new UpdateOptions { IsUpsert = true },
            ct);

    public async Task<List<string>> TopByScoreAsync(string entityType, int limit, CancellationToken ct = default)
    {
        if (limit <= 0) return [];

        var rows = await _stats
            .Find(Builders<EntityStats>.Filter.Eq(s => s.EntityType, entityType))
            .Sort(Builders<EntityStats>.Sort.Descending(s => s.HotScore))
            .Limit(limit)
            .Project(s => s.EntityId)
            .ToListAsync(ct);

        return rows;
    }

    public async Task<HashSet<string>> WellObservedEntityIdsAsync(
        string entityType, int minImpressions, CancellationToken ct = default)
    {
        var ids = await _stats
            .Find(Builders<EntityStats>.Filter.Eq(s => s.EntityType, entityType) &
                  Builders<EntityStats>.Filter.Gte(s => s.Impressions, minImpressions))
            .Project(s => s.EntityId)
            .ToListAsync(ct);

        return ids.ToHashSet();
    }

    public async Task<List<InterestTriple>> CollapseTriplesAsync(DateTime since, CancellationToken ct = default)
    {
        // The collapse happens in Mongo rather than in the job: pulling raw events out to
        // deduplicate them in memory would move the whole retention window across the wire,
        // while the grouped result is bounded by (entities × users × 5 actions) actually seen.
        var pipeline = new[]
        {
            new BsonDocument("$match", new BsonDocument("ts", new BsonDocument("$gte", since))),
            new BsonDocument("$group", new BsonDocument
            {
                ["_id"] = new BsonDocument
                {
                    ["entity_type"] = "$entity_type",
                    ["entity_id"]   = "$entity_id",
                    ["user_id"]     = "$user_id",
                    ["action"]      = "$action",
                },
                ["latest_ts"] = new BsonDocument("$max", "$ts"),
            }),
        };

        var rows = await _events
            .Aggregate<BsonDocument>(pipeline, new AggregateOptions { AllowDiskUse = true }, ct)
            .ToListAsync(ct);

        return rows.Select(row =>
        {
            var key = row["_id"].AsBsonDocument;
            return new InterestTriple(
                key["entity_type"].AsString,
                key["entity_id"].AsString,
                key["user_id"].AsString,
                key["action"].AsString,
                row["latest_ts"].ToUniversalTime());
        }).ToList();
    }

    public async Task WriteStatsAsync(
        IReadOnlyList<EntityScore> scores, DateTime windowEnd, CancellationToken ct = default)
    {
        if (scores.Count == 0) return;

        var writes = scores.Select(score => (WriteModel<EntityStats>)new UpdateOneModel<EntityStats>(
            Builders<EntityStats>.Filter.Eq(s => s.EntityType, score.EntityType) &
            Builders<EntityStats>.Filter.Eq(s => s.EntityId,   score.EntityId),
            Builders<EntityStats>.Update
                .Set(s => s.HotScore,    score.HotScore)
                .Set(s => s.Impressions, score.Impressions)
                .Set(s => s.Actors,      score.Actors)
                // entity_type / entity_id come from the filter on insert — see UpsertSearchGapAsync.
                .Set(s => s.WindowEnd,   windowEnd))
        {
            IsUpsert = true,
        }).ToList();

        await _stats.BulkWriteAsync(writes, new BulkWriteOptions { IsOrdered = false }, ct);
    }

    public async Task<long> DeleteStatsForMissingEntitiesAsync(
        string entityType, IReadOnlyCollection<string> existingIds, CancellationToken ct = default)
    {
        // An empty catalog is far more likely to be a failed read than a genuinely empty
        // collection, and acting on it would wipe every score. Do nothing instead.
        if (existingIds.Count == 0) return 0;

        var result = await _stats.DeleteManyAsync(
            Builders<EntityStats>.Filter.Eq(s => s.EntityType, entityType) &
            Builders<EntityStats>.Filter.Nin(s => s.EntityId, existingIds),
            ct);

        return result.DeletedCount;
    }
}
