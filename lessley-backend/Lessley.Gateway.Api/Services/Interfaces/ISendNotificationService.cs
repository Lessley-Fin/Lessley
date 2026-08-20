namespace Lessley.Gateway.Api.Services.Interfaces;

public interface ISendNotificationService
{
    Task<int> SendToUserAsync(string userId, string message, string? dealId = null, string type = "user", CancellationToken ct = default);
    Task SendToGroupAsync(string groupTag, string message, string? dealId = null, CancellationToken ct = default);
    Task<int> SendToAllAsync(string message, CancellationToken ct = default);
}
