namespace Lessley.Gateway.Api.Contracts;

public record SendUserNotificationCommand(string UserId, string Message);
