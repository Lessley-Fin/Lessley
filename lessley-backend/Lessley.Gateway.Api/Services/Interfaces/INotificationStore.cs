using Lessley.Gateway.Api.Models;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface INotificationStore
{
    Task SaveAsync(Notification notification, CancellationToken ct = default);
}
