namespace Lessley.Gateway.Api.Contracts;

/// <summary>
/// Asks Personalization to recalculate a user's spending categories. The result comes back as
/// a <see cref="UserTagAssignedEvent"/> — Personalization never writes them itself.
/// </summary>
/// <remarks>Days mirrors Personalization's LIMITS.DAYS; keep the two in step.</remarks>
public record CalculateUserCategoriesCommand(string UserId, int Days = 90);
