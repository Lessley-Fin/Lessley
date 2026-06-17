using MongoDB.Bson;

namespace Lessley.Gateway.Api.Models;

public class Notification
{
    public ObjectId Id { get; set; } = ObjectId.GenerateNewId();
    public string TargetId { get; set; } = string.Empty;    // userId, group tag, or dealId
    public string TargetType { get; set; } = string.Empty;  // "user" | "group" | "deal"
    public string Message { get; set; } = string.Empty;
    public string? DealId { get; set; }
    public List<string>? Categories { get; set; }           // populated for deal notifications
    public DateTime SentAt { get; set; }
}
