using MongoDB.Bson;

namespace Lessley.Gateway.Api.Models;

/// <summary>
/// A registration that has been started but not finished. Nothing exists in Identity while this
/// document does — the <c>ApplicationUser</c> is created only by the final "complete" call, so
/// abandoning the wizard leaves no account behind. The document self-destructs via a Mongo TTL
/// index on <see cref="ExpiresAt"/>, which is what forces an abandoned signup to restart from
/// step one.
/// </summary>
public class PendingRegistration
{
    public ObjectId Id { get; set; } = ObjectId.GenerateNewId();

    /// <summary>
    /// Hash of the opaque handle the client quotes on every later step. A separate high-entropy
    /// token rather than <see cref="Id"/>, because an ObjectId is a timestamp plus a counter —
    /// guessable, and guessing one would let a stranger finish someone else's verified signup.
    /// </summary>
    public string TokenHash { get; set; } = string.Empty;

    public string UserName { get; set; } = string.Empty;

    /// <summary>Upper-cased, for case-insensitive collision checks against Identity's normalized columns.</summary>
    public string NormalizedUserName { get; set; } = string.Empty;

    public string Email { get; set; } = string.Empty;

    public string NormalizedEmail { get; set; } = string.Empty;

    /// <summary>
    /// Hashed with the same Identity <c>IPasswordHasher</c> the real user will use, so the plaintext
    /// password never rests here and the hash transfers verbatim on completion.
    /// </summary>
    public string PasswordHash { get; set; } = string.Empty;

    // Collected by later wizard steps and supplied to the completion call.
    public List<string> Clubs { get; set; } = new();
    public List<string> MutedCategories { get; set; } = new();
    public double? MatchingScore { get; set; }

    public string CodeHash { get; set; } = string.Empty;
    public DateTime CodeExpiresAt { get; set; }

    /// <summary>Wrong code guesses so far. Burns the code once it hits the configured maximum.</summary>
    public int Attempts { get; set; }

    /// <summary>Codes emailed for this registration, including the first one.</summary>
    public int SendCount { get; set; }
    public DateTime LastSentAt { get; set; }

    public bool EmailVerified { get; set; }

    public DateTime CreatedAt { get; set; }
    public DateTime ExpiresAt { get; set; }

    public bool IsExpired => DateTime.UtcNow >= ExpiresAt;
    public bool IsCodeExpired => DateTime.UtcNow >= CodeExpiresAt;
}
