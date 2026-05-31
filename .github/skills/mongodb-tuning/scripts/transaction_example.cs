using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using MongoDB.Driver;
using MongoDB.Bson;
using Microsoft.Extensions.Logging;

namespace Lessley.DataIntelligence.Transactions
{
    /// <summary>
    /// MongoDB Transaction Examples for C# (.NET)
    /// 
    /// For Lessley.Gateway.Api and Lessley.DataIntelligence
    /// 
    /// Usage:
    ///     var txService = new MongoTransactionService(mongoClient);
    ///     bool success = await txService.AddClubCardAsync("user-123", "hever", 
    ///         new Dictionary<string, object> {
    ///             {"phone", "0543334422"},
    ///             {"email", "user@example.com"}
    ///         });
    /// </summary>
    public class MongoTransactionService
    {
        private readonly IMongoClient _client;
        private readonly IMongoDatabase _db;
        private readonly ILogger<MongoTransactionService> _logger;
        private readonly int _maxRetries = 3;

        public MongoTransactionService(IMongoClient client, string dbName, ILogger<MongoTransactionService> logger)
        {
            _client = client;
            _db = client.GetDatabase(dbName);
            _logger = logger;
        }

        // =====================================================================
        // Transaction 1: Add Club Card (Atomicity: profile + analytics)
        // =====================================================================

        /// <summary>
        /// Add a club card to user profile and atomically recalculate savings.
        /// If either step fails, both are rolled back.
        /// </summary>
        public async Task<bool> AddClubCardAsync(
            string userId,
            string clubName,
            Dictionary<string, object> clubMetadata = null)
        {
            for (int attempt = 0; attempt < _maxRetries; attempt++)
            {
                IClientSessionHandle session = null;

                try
                {
                    session = await _client.StartSessionAsync();
                    session.StartTransaction();

                    var usersCollection = _db.GetCollection<BsonDocument>("users");
                    var analyticsCollection = _db.GetCollection<BsonDocument>("analytics");

                    // ─────────────────────────────────────────────────────────────
                    // Step 1: Add club card to user profile
                    // ─────────────────────────────────────────────────────────────

                    var clubRecord = new BsonDocument
                    {
                        { "name", clubName },
                        { "metadata", clubMetadata != null ? new BsonDocument(clubMetadata) : new BsonDocument() },
                        { "added_at", DateTime.UtcNow },
                        { "status", "active" }
                    };

                    var updateResult = await usersCollection.UpdateOneAsync(
                        session,
                        Builders<BsonDocument>.Filter.Eq("_id", userId),
                        Builders<BsonDocument>.Update
                            .Push("clubs", clubRecord)
                            .Inc("club_count", 1)
                            .Set("updated_at", DateTime.UtcNow)
                    );

                    if (updateResult.MatchedCount == 0)
                    {
                        _logger.LogWarning($"User not found: {userId}");
                        await session.AbortTransactionAsync();
                        return false;
                    }

                    _logger.LogInformation($"Added club card '{clubName}' to user {userId}");

                    // ─────────────────────────────────────────────────────────────
                    // Step 2: Fetch updated user and recalculate savings
                    // ─────────────────────────────────────────────────────────────

                    var updatedUser = await usersCollection.Find(session, Builders<BsonDocument>.Filter.Eq("_id", userId))
                        .FirstOrDefaultAsync();

                    if (updatedUser == null)
                    {
                        _logger.LogError($"User disappeared mid-transaction: {userId}");
                        await session.AbortTransactionAsync();
                        return false;
                    }

                    // Calculate new savings based on all clubs
                    var newSavings = CalculateUserSavings(updatedUser);

                    // ─────────────────────────────────────────────────────────────
                    // Step 3: Update analytics collection
                    // ─────────────────────────────────────────────────────────────

                    var clubs = updatedUser.GetValue("clubs", new BsonArray()).AsBsonArray;

                    await analyticsCollection.UpdateOneAsync(
                        session,
                        Builders<BsonDocument>.Filter.Eq("user_id", userId),
                        Builders<BsonDocument>.Update
                            .Set("total_savings", newSavings)
                            .Set("club_count", clubs.Count)
                            .Set("last_club_added", clubName)
                            .Set("updated_at", DateTime.UtcNow),
                        new UpdateOptions { IsUpsert = true }
                    );

                    _logger.LogInformation($"Updated analytics: savings={newSavings}, clubs={clubs.Count}");

                    // ─────────────────────────────────────────────────────────────
                    // Commit: all operations succeed together
                    // ─────────────────────────────────────────────────────────────

                    await session.CommitTransactionAsync();
                    _logger.LogInformation($"Transaction committed for user {userId}");
                    return true;
                }
                catch (MongoServerSelectionException ex) when (attempt < _maxRetries - 1)
                {
                    // Transient network error: retry with exponential backoff
                    var backoff = 0.5 * Math.Pow(2, attempt);
                    _logger.LogWarning($"Attempt {attempt + 1} failed (network error), retrying in {backoff}s...");
                    await Task.Delay((int)(backoff * 1000));
                }
                catch (MongoCommandException ex)
                {
                    // Logical error: don't retry
                    _logger.LogError($"Transaction failed (logical error): {ex.Message}");
                    if (session?.IsInTransaction ?? false)
                    {
                        await session.AbortTransactionAsync();
                    }
                    return false;
                }
                catch (Exception ex)
                {
                    _logger.LogError($"Unexpected error during transaction: {ex.Message}");
                    if (session?.IsInTransaction ?? false)
                    {
                        await session.AbortTransactionAsync();
                    }
                    throw;
                }
                finally
                {
                    session?.Dispose();
                }
            }

            return false;
        }

        // =====================================================================
        // Transaction 2: Recalculate User Savings
        // =====================================================================

        /// <summary>
        /// Atomically recalculate user savings across all clubs and update both
        /// users and analytics collections.
        /// </summary>
        public async Task<double?> RecalculateUserSavingsAsync(string userId)
        {
            IClientSessionHandle session = null;

            try
            {
                session = await _client.StartSessionAsync();
                session.StartTransaction();

                var usersCollection = _db.GetCollection<BsonDocument>("users");
                var analyticsCollection = _db.GetCollection<BsonDocument>("analytics");
                var savingsLogCollection = _db.GetCollection<BsonDocument>("savings_log");

                // Step 1: Fetch current user state
                var user = await usersCollection.Find(session, Builders<BsonDocument>.Filter.Eq("_id", userId))
                    .FirstOrDefaultAsync();

                if (user == null)
                {
                    _logger.LogWarning($"User not found for savings recalculation: {userId}");
                    await session.AbortTransactionAsync();
                    return null;
                }

                // Step 2: Calculate savings
                var newSavings = CalculateUserSavings(user);

                // Step 3: Update users collection
                await usersCollection.UpdateOneAsync(
                    session,
                    Builders<BsonDocument>.Filter.Eq("_id", userId),
                    Builders<BsonDocument>.Update
                        .Set("estimated_savings", newSavings)
                        .Set("savings_calculated_at", DateTime.UtcNow)
                );

                // Step 4: Update analytics
                var clubs = user.GetValue("clubs", new BsonArray()).AsBsonArray;

                await analyticsCollection.UpdateOneAsync(
                    session,
                    Builders<BsonDocument>.Filter.Eq("user_id", userId),
                    Builders<BsonDocument>.Update
                        .Set("total_savings", newSavings)
                        .Set("updated_at", DateTime.UtcNow),
                    new UpdateOptions { IsUpsert = true }
                );

                // Step 5: Log the recalculation event
                var logEntry = new BsonDocument
                {
                    { "user_id", userId },
                    { "savings", newSavings },
                    { "club_count", clubs.Count },
                    { "timestamp", DateTime.UtcNow }
                };

                await savingsLogCollection.InsertOneAsync(session, logEntry);

                // Commit
                await session.CommitTransactionAsync();
                _logger.LogInformation($"Savings recalculated and committed for user {userId}: ${newSavings:F2}");
                return newSavings;
            }
            catch (MongoCommandException ex)
            {
                _logger.LogError($"Savings recalculation failed: {ex.Message}");
                if (session?.IsInTransaction ?? false)
                {
                    await session.AbortTransactionAsync();
                }
                return null;
            }
            finally
            {
                session?.Dispose();
            }
        }

        // =====================================================================
        // Transaction 3: Batch User Migration with Atomicity
        // =====================================================================

        /// <summary>
        /// Atomically migrate a user to new schema version, updating
        /// multiple related collections.
        /// </summary>
        public async Task<bool> MigrateUserToV2SchemaAsync(string userId)
        {
            IClientSessionHandle session = null;

            try
            {
                session = await _client.StartSessionAsync();
                session.StartTransaction();

                var usersCollection = _db.GetCollection<BsonDocument>("users");
                var analyticsCollection = _db.GetCollection<BsonDocument>("analytics");
                var auditLogCollection = _db.GetCollection<BsonDocument>("audit_log");

                // Step 1: Update user to v2 schema
                await usersCollection.UpdateOneAsync(
                    session,
                    Builders<BsonDocument>.Filter.Eq("_id", userId),
                    Builders<BsonDocument>.Update
                        .Set("schema_version", 2)
                        .Set("migrated_at", DateTime.UtcNow)
                        .Unset("legacy_field")
                );

                // Step 2: Create analytics record if missing
                await analyticsCollection.UpdateOneAsync(
                    session,
                    Builders<BsonDocument>.Filter.Eq("user_id", userId),
                    Builders<BsonDocument>.Update
                        .Set("schema_version", 2)
                        .Set("migrated_at", DateTime.UtcNow),
                    new UpdateOptions { IsUpsert = true }
                );

                // Step 3: Mark migration in audit log
                var auditEntry = new BsonDocument
                {
                    { "action", "schema_migration" },
                    { "user_id", userId },
                    { "from_version", 1 },
                    { "to_version", 2 },
                    { "timestamp", DateTime.UtcNow }
                };

                await auditLogCollection.InsertOneAsync(session, auditEntry);

                // Commit
                await session.CommitTransactionAsync();
                _logger.LogInformation($"User {userId} migrated to v2 schema");
                return true;
            }
            catch (MongoCommandException ex)
            {
                _logger.LogError($"Migration failed: {ex.Message}");
                if (session?.IsInTransaction ?? false)
                {
                    await session.AbortTransactionAsync();
                }
                return false;
            }
            finally
            {
                session?.Dispose();
            }
        }

        // =====================================================================
        // Helper Methods
        // =====================================================================

        private double CalculateUserSavings(BsonDocument user)
        {
            var clubs = user.GetValue("clubs", new BsonArray()).AsBsonArray;

            // Stub: assume each club grants $10/month base
            double basePerClub = 10.0;
            double total = basePerClub * clubs.Count;

            // In production, this would call:
            // - A discount engine service
            // - Query deal history and apply real rates
            // - Consider seasonal variations

            return total;
        }
    }

    // =========================================================================
    // Dependency Injection Setup
    // =========================================================================

    public static class MongoTransactionServiceExtensions
    {
        /// <summary>
        /// Register MongoTransactionService in DI container.
        /// 
        /// Usage in Startup.cs or Program.cs:
        ///     services.AddMongoTransactions(Configuration["ConnectionStrings:MongoDB"], "lessley");
        /// </summary>
        public static IServiceCollection AddMongoTransactions(
            this IServiceCollection services,
            string mongoUri,
            string dbName)
        {
            var mongoClient = new MongoClient(mongoUri);

            services.AddSingleton<IMongoClient>(mongoClient);
            services.AddScoped<MongoTransactionService>();

            return services;
        }
    }
}
