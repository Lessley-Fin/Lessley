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
        // Speeds up the fanout query in SendToGroupAsync: find all users with a given tag
        var col = db.GetCollection<BsonDocument>("users");

        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("Tags"),
            new CreateIndexOptions { Name = "idx_tags" }
        ));
    }
}
