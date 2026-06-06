using MongoDB.Bson;

namespace Lessley.Gateway.Api.Models;

public class Notification
{
    public ObjectId Id { get; set; } = ObjectId.GenerateNewId();
    public string TargetId { get; set; } = string.Empty;   // userId or group tag
    public string TargetType { get; set; } = string.Empty; // "user" | "group"
    public string Message { get; set; } = string.Empty;
    public string? DealId { get; set; }
    public DateTime SentAt { get; set; }
    public bool IsRead { get; set; }
}
