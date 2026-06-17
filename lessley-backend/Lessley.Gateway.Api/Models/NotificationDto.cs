using MongoDB.Bson;

namespace Lessley.Gateway.Api.Models;

public class NotificationDto
{
    public string Id { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public string? DealId { get; set; }
    public DateTime SentAt { get; set; }
    public string TargetType { get; set; } = string.Empty;
    public bool IsRead { get; set; }
    public DateTime? ReadAt { get; set; }

    public List<string>? Categories { get; set; }

    public static NotificationDto From(Notification notification, NotificationRead read) => new()
    {
        Id         = notification.Id.ToString(),
        Message    = notification.Message,
        DealId     = notification.DealId,
        Categories = notification.Categories,
        SentAt     = notification.SentAt,
        TargetType = notification.TargetType,
        IsRead     = read.IsRead,
        ReadAt     = read.ReadAt,
    };
}
