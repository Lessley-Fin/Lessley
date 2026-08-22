using MongoDB.Bson;
using MongoDB.Driver;

namespace Lessley.Gateway.Api.Data;

public static class MongoIndexInitializer
{
    private static readonly TimeSpan Ttl = TimeSpan.FromDays(90);

    /// <summary>Retention for raw engagement events — the 30-day scoring window plus slack.</summary>
    private static readonly TimeSpan InterestEventTtl = TimeSpan.FromDays(40);

    public static async Task CreateIndexesAsync(string connectionString, string databaseName)
    {
        var client = new MongoClient(connectionString);
        var db     = client.GetDatabase(databaseName);

        await CreateNotificationIndexesAsync(db);
        await CreateUserTagIndexAsync(db);
        await CreateDealFinderIndexesAsync(db);
        await CreateRefreshTokenIndexesAsync(db);
        await CreatePendingRegistrationIndexesAsync(db);
        await CreateVerificationCodeIndexesAsync(db);
        await CreateInterestIndexesAsync(db);
    }

    private static async Task CreateInterestIndexesAsync(IMongoDatabase db)
    {
        var events = db.GetCollection<BsonDocument>("interest_events");
        var stats  = db.GetCollection<BsonDocument>("entity_stats");
        var gaps   = db.GetCollection<BsonDocument>("search_gaps");

        // Idempotent ingest: the client retries a flush it could not confirm, and this is what
        // makes the retry cost nothing. Without it a flaky connection inflates the ranking.
        await events.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("event_id"),
            new CreateIndexOptions { Name = "uq_interest_event_id", Unique = true }
        ));

        // TTL doubling as the retention policy: raw events exist only to be collapsed by the
        // rollup, so one past the scoring window has no remaining purpose. Slightly longer
        // than the 30-day window so a missed run still has a full window to score.
        await events.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("ts"),
            new CreateIndexOptions { ExpireAfter = InterestEventTtl, Name = "ttl_interest_event_ts" }
        ));

        // The rollup's $match/$group path.
        await events.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("entity_type").Ascending("entity_id").Ascending("ts"),
            new CreateIndexOptions { Name = "idx_interest_entity_ts" }
        ));

        // Per-user history — supports a subject-access export or deletion without a scan.
        await events.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("user_id").Ascending("ts"),
            new CreateIndexOptions { Name = "idx_interest_user_ts" }
        ));

        // The hot endpoint's read: top N by score for one entity type.
        await stats.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("entity_type").Descending("hot_score"),
            new CreateIndexOptions { Name = "idx_entity_stats_type_score" }
        ));

        // One row per entity — the rollup upserts against this key.
        await stats.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("entity_type").Ascending("entity_id"),
            new CreateIndexOptions { Name = "uq_entity_stats_type_id", Unique = true }
        ));

        // One row per normalized query, so the upsert counts rather than duplicates.
        await gaps.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("query_norm"),
            new CreateIndexOptions { Name = "uq_search_gap_query", Unique = true }
        ));

        // Read path: what users want most that the catalog does not carry.
        await gaps.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Descending("hits"),
            new CreateIndexOptions { Name = "idx_search_gap_hits" }
        ));
    }

    private static async Task CreatePendingRegistrationIndexesAsync(IMongoDatabase db)
    {
        var col = db.GetCollection<BsonDocument>("pending_registrations");

        // TTL — an abandoned signup disappears on its own once ExpiresAt passes, which is what
        // makes "if the user stops registering, they start from the beginning" true without a
        // cleanup job. Services still check ExpiresAt themselves, since Mongo's TTL monitor only
        // sweeps about once a minute.
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("ExpiresAt"),
            new CreateIndexOptions { ExpireAfter = TimeSpan.Zero, Name = "ttl_pending_registration_expiresAt" }
        ));

        // One in-flight registration per address: the second "start" for an email replaces the
        // first rather than racing it.
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("NormalizedEmail"),
            new CreateIndexOptions { Name = "uq_pending_registration_email", Unique = true }
        ));

        // Username collision check at "start".
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("NormalizedUserName"),
            new CreateIndexOptions { Name = "idx_pending_registration_userName" }
        ));

        // Every step after "start" finds its registration by the hashed handle the client quotes.
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("TokenHash"),
            new CreateIndexOptions { Name = "idx_pending_registration_tokenHash" }
        ));
    }

    private static async Task CreateVerificationCodeIndexesAsync(IMongoDatabase db)
    {
        var col = db.GetCollection<BsonDocument>("verification_codes");

        // TTL — expired reset/login codes evaporate rather than accumulating.
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("ExpiresAt"),
            new CreateIndexOptions { ExpireAfter = TimeSpan.Zero, Name = "ttl_verification_code_expiresAt" }
        ));

        // At most one live code per flow per address — requesting a new code overwrites the old
        // one, so only the newest code an address received can ever be redeemed.
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("Purpose").Ascending("NormalizedEmail"),
            new CreateIndexOptions { Name = "uq_verification_code_purpose_email", Unique = true }
        ));
    }

    private static async Task CreateRefreshTokenIndexesAsync(IMongoDatabase db)
    {
        var col = db.GetCollection<BsonDocument>("refresh_tokens");

        // TTL — purge refresh tokens once past their Expires timestamp (ExpireAfter zero
        // means "expire exactly at the Expires value").
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("Expires"),
            new CreateIndexOptions { ExpireAfter = TimeSpan.Zero, Name = "ttl_refresh_expires" }
        ));

        // Lookup by hashed token value on refresh/logout.
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("Token"),
            new CreateIndexOptions { Name = "idx_refresh_token" }
        ));
    }

    private static async Task CreateNotificationIndexesAsync(IMongoDatabase db)
    {
        var col = db.GetCollection<BsonDocument>("notifications");

        // TTL — expire notifications after 90 days
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("SentAt"),
            new CreateIndexOptions { ExpireAfter = Ttl, Name = "ttl_sentAt" }
        ));

        // Primary read path: all notifications for a user, newest first
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("UserId").Descending("SentAt"),
            new CreateIndexOptions { Name = "idx_userId_sentAt" }
        ));

        // Mark-as-read lookup: find a specific notification for a user
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("UserId").Ascending("IsRead"),
            new CreateIndexOptions { Name = "idx_userId_isRead" }
        ));
    }

    private static async Task CreateUserTagIndexAsync(IMongoDatabase db)
    {
        var col = db.GetCollection<BsonDocument>("users");

        // Speeds up the fanout query in SendToGroupAsync: find all users with a given tag
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("Tags"),
            new CreateIndexOptions { Name = "idx_tags" }
        ));

        // Enforce one account per email at the DB level (defense-in-depth with Identity's
        // RequireUniqueEmail): FindByEmailAsync does a SingleOrDefault, so a second user with
        // the same email would 500 every email-keyed lookup (/me, settings, tags). Partial
        // filter so users without a NormalizedEmail don't collide on a shared null.
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("NormalizedEmail"),
            new CreateIndexOptions<BsonDocument>
            {
                Name                    = "uq_users_normalizedEmail",
                Unique                  = true,
                PartialFilterExpression = Builders<BsonDocument>.Filter.Exists("NormalizedEmail"),
            }
        ));
    }

    private static async Task CreateDealFinderIndexesAsync(IMongoDatabase db)
    {
        // The pipeline's own collections. It creates its own indexes on write
        // (store_id on deals, name_forms.normalized on stores); these are the ones
        // deal search needs on top of those.
        var stores = db.GetCollection<BsonDocument>("stores");
        var deals  = db.GetCollection<BsonDocument>("deals");

        // stores: MCC $in filter on array field
        await stores.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("metadata.mcc_codes"),
            new CreateIndexOptions { Name = "idx_store_mcc_codes" }
        ));

        // stores: store name for sort / projection alongside $regex
        await stores.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("name"),
            new CreateIndexOptions { Name = "idx_store_name" }
        ));

        // deals: join key for the $in lookup from matching store IDs
        await deals.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("store_id"),
            new CreateIndexOptions { Name = "idx_deal_store_id" }
        ));

        // deals: title for $regex deal-text search
        await deals.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("title"),
            new CreateIndexOptions { Name = "idx_deal_title" }
        ));
    }
}
