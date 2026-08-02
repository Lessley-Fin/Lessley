namespace Lessley.Gateway.Api.Models;

public class NotificationDto
{
    public string Id { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public string? DealId { get; set; }
    public DateTime SentAt { get; set; }
    public string Type { get; set; } = string.Empty;
    public string? CalcType { get; set; }
    public string? Data { get; set; }
    public bool IsRead { get; set; }
    public DateTime? ReadAt { get; set; }
    public List<string>? Categories { get; set; }

    public static NotificationDto From(Notification n) => new()
    {
        Id         = n.Id.ToString(),
        Message    = n.Message,
        DealId     = n.DealId,
        Categories = n.Categories,
        CalcType   = n.CalcType,
        Data       = n.Data,
        SentAt     = n.SentAt,
        Type       = n.Type,
        IsRead     = n.IsRead,
        ReadAt     = n.ReadAt,
    };
}
