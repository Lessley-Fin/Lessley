using Lessley.Gateway.Api.Models;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface INotificationRepository
{
    Task SaveAsync(Notification notification, CancellationToken ct = default);

    /// <summary>
    /// Returns all notifications for a user:
    ///   • direct user notifications (TargetId == userId, TargetType == "user")
    ///   • group notifications for tags the user belongs to (TargetType == "group", TargetId in groupTags)
    ///
    /// For high-scale apps consider a fanout-on-write approach (one Notification row per recipient)
    /// so this query stays O(1) per user rather than scanning all group rows.
    /// </summary>
    Task<List<Notification>> GetByUserAsync(string userId, string[] groupTags, CancellationToken ct = default);

    /// <summary>Marks all direct user notifications as read. Group notifications have no per-user read state in this model.</summary>
    Task MarkAllAsReadAsync(string userId, CancellationToken ct = default);
}
