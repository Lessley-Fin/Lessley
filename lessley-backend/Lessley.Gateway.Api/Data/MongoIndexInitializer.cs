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
        await CreateNotificationReadIndexesAsync(db);
        await CreateUserTagIndexAsync(db);
    }

    private static async Task CreateNotificationIndexesAsync(IMongoDatabase db)
    {
        var col = db.GetCollection<BsonDocument>("notifications");

        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("SentAt"),
            new CreateIndexOptions { ExpireAfter = Ttl, Name = "ttl_sentAt" }
        ));
    }

    private static async Task CreateNotificationReadIndexesAsync(IMongoDatabase db)
    {
        var col = db.GetCollection<BsonDocument>("notification_reads");

        // TTL — expire read records alongside their parent notification
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("CreatedAt"),
            new CreateIndexOptions { ExpireAfter = Ttl, Name = "ttl_createdAt" }
        ));

        // Fetch all reads for a user quickly (primary read path)
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("UserId").Descending("CreatedAt"),
            new CreateIndexOptions { Name = "idx_userId_createdAt" }
        ));

        // Look up reads by notification ID (used in MarkAsReadAsync)
        await col.Indexes.CreateOneAsync(new CreateIndexModel<BsonDocument>(
            Builders<BsonDocument>.IndexKeys.Ascending("NotificationId"),
            new CreateIndexOptions { Name = "idx_notificationId" }
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
