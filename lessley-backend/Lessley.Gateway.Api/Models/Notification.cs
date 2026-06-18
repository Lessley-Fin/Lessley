using MongoDB.Bson;

namespace Lessley.Gateway.Api.Models;

public class Notification
{
    public ObjectId Id { get; set; } = ObjectId.GenerateNewId();
    public string UserId { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public string? DealId { get; set; }
    public List<string>? Categories { get; set; }
    public string Type { get; set; } = string.Empty;  // "user" | "group" | "deal" | "calc"
    public bool IsRead { get; set; }
    public DateTime? ReadAt { get; set; }
    public DateTime SentAt { get; set; }
}
