using MongoDB.Bson;

namespace Lessley.Gateway.Api.Models;

/// <summary>
/// One live emailed code for an existing user, for either password reset or passwordless login.
/// At most one document exists per (purpose, email): re-requesting overwrites the code, so an
/// older code stops working the moment a newer one is sent. Purged by a TTL index on
/// <see cref="ExpiresAt"/>.
/// </summary>
public class VerificationCode
{
    public ObjectId Id { get; set; } = ObjectId.GenerateNewId();

    /// <summary>The <c>VerificationPurpose</c> name. Stored as a string so it stays readable in Mongo.</summary>
    public string Purpose { get; set; } = string.Empty;

    public string NormalizedEmail { get; set; } = string.Empty;

    public string UserId { get; set; } = string.Empty;

    public string CodeHash { get; set; } = string.Empty;
    public DateTime CodeExpiresAt { get; set; }

    public int Attempts { get; set; }
    public int SendCount { get; set; }
    public DateTime LastSentAt { get; set; }

    /// <summary>
    /// Password reset only: hash of the single-use ticket issued once the code is verified. It
    /// separates "proved you own the mailbox" from "set the new password", so the second request
    /// does not have to carry the code around again.
    /// </summary>
    public string? TicketHash { get; set; }
    public DateTime? TicketExpiresAt { get; set; }

    public DateTime CreatedAt { get; set; }
    public DateTime ExpiresAt { get; set; }

    public bool IsCodeExpired => DateTime.UtcNow >= CodeExpiresAt;
    public bool IsTicketExpired => TicketExpiresAt is null || DateTime.UtcNow >= TicketExpiresAt;
}
