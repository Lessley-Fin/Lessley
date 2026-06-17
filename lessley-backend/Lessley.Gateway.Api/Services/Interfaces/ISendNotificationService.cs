namespace Lessley.Gateway.Api.Services.Interfaces;

public interface ISendNotificationService
{
    Task<int> SendToUserAsync(string userId, string message, string? dealId = null, CancellationToken ct = default);
    Task SendToGroupAsync(string groupTag, string message, string? dealId = null, CancellationToken ct = default);

    /// <summary>
    /// Sends ONE notification per deal across all matching category groups, deduplicating
    /// recipients so a user who matches multiple categories receives only one notification.
    /// </summary>
    Task SendDealNotificationAsync(string dealId, string message, string[] categories, CancellationToken ct = default);
}
