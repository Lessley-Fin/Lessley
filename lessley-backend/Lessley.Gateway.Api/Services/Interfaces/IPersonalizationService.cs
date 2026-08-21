namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IPersonalizationService
{
    /// <summary>Publishes a category-recalculation command via RabbitMQ.</summary>
    Task TriggerCalculateUserCategoriesAsync(string userId, int days = 90, CancellationToken ct = default);
}
