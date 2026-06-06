namespace Lessley.Gateway.Api.Services.Interfaces;

public interface ISendNotificationService
{
    Task<int> SendToUserAsync(string userId, string message, CancellationToken ct = default);
    Task SendToGroupAsync(string groupTag, string message, CancellationToken ct = default);
}
