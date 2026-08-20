using MongoDB.Bson;

namespace Lessley.Gateway.Api.Models;

public class Notification
{
    public ObjectId Id { get; set; } = ObjectId.GenerateNewId();
    public string UserId { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public string? DealId { get; set; }
    public List<string>? Categories { get; set; }
    public string Type { get; set; } = string.Empty;  // "user" | "group" | "deal" | "calc" | "all" | "welcome"
    public string? CalcType { get; set; }             // "missed-savings" | "matching-clubs" (when Type == "calc")
    public string? Data { get; set; }                 // raw JSON payload for calc notifications
    public bool IsRead { get; set; }
    public DateTime? ReadAt { get; set; }
    public DateTime SentAt { get; set; }
}
