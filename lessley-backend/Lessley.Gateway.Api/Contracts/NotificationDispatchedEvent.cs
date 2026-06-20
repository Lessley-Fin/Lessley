namespace Lessley.Gateway.Api.Contracts;

public record NotificationDispatchedEvent(
    string NotificationId,
    string Type,
    int RecipientCount,
    string RequestId,
    DateTime SentAt);
