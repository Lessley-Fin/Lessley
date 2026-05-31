using System.ComponentModel.DataAnnotations;

namespace Lessley.Gateway.Api.Models;

public record SendNotificationDto(
    [Required, MinLength(1)] string Message
);
