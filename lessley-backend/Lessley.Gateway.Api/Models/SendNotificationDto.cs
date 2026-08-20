using System.ComponentModel.DataAnnotations;

namespace Lessley.Gateway.Api.Models;

public record SendNotificationDto(
    [Required, MinLength(1)] string Message,
    string? DealId = null
);

public record BroadcastNotificationDto(
    [Required, MinLength(1)] string Message
);
