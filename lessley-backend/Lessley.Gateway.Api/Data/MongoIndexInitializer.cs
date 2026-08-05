using MongoDB.Bson;
using MongoDB.Driver;

namespace Lessley.Gateway.Api.Data;

public static class MongoIndexInitializer
{
    private static readonly TimeSpan Ttl = TimeSpan.FromDays(90);

    public static async Task CreateIndexesAsync(string connectionString, string databaseName)
    {
        var client = new MongoClient(connectionString);
        var db     = client.GetDatabase(databaseName);

        await CreateNotificationIndexesAsync(db);
        await CreateUserTagIndexAsync(db);
        await CreateDealFinderIndexesAsync(db);
        await CreateRefreshTokenIndexesAsync(db);
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
        var stores = db.GetCollection<BsonDocument>("store_list");
        var deals  = db.GetCollection<BsonDocument>("deal_list");

        // store_list: MCC $in filter on array field
        await stores.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("metadata.mcc_codes"),
            new CreateIndexOptions { Name = "idx_store_mcc_codes" }
        ));

        // store_list: store name for sort / projection alongside $regex
        await stores.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("name"),
            new CreateIndexOptions { Name = "idx_store_name" }
        ));

        // deal_list: join key for the $in lookup from matching store IDs
        await deals.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("store_id"),
            new CreateIndexOptions { Name = "idx_deal_store_id" }
        ));

        // deal_list: title for $regex deal-text search
        await deals.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("title"),
            new CreateIndexOptions { Name = "idx_deal_title" }
        ));
    }
}
