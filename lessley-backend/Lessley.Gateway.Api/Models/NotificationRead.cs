using MongoDB.Bson;

namespace Lessley.Gateway.Api.Models;

public class NotificationRead
{
    public ObjectId Id { get; set; } = ObjectId.GenerateNewId();
    public ObjectId NotificationId { get; set; }
    public string UserId { get; set; } = string.Empty;
    public bool IsRead { get; set; }
    public DateTime? ReadAt { get; set; }
    public DateTime CreatedAt { get; set; }
}
