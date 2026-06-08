using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;

namespace Lessley.Gateway.Api.Services.Classes;

public class NotificationService : INotificationService
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly INotificationRepository _notificationRepository;

    public NotificationService(
        UserManager<ApplicationUser> userManager,
        INotificationRepository notificationRepository)
    {
        _userManager            = userManager;
        _notificationRepository = notificationRepository;
    }

    public async Task<List<Notification>> GetUserNotificationsAsync(string userId, CancellationToken ct = default)
    {
        var user  = await _userManager.FindByIdAsync(userId);
        var muted = user?.MutedTags ?? new List<string>();

        // A muted category must never surface in a user's notifications, even in history.
        var groupTags = (user?.Tags ?? new List<string>())
            .Where(t => !muted.Contains(t))
            .ToArray();

        return await _notificationRepository.GetByUserAsync(userId, groupTags, ct);
    }

    public Task MarkUserNotificationsAsReadAsync(string userId, CancellationToken ct = default)
        => _notificationRepository.MarkAllAsReadAsync(userId, ct);
}
