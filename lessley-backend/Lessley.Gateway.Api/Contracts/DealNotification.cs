namespace Lessley.Gateway.Api.Contracts;

public record DealNotification(string DealId, string Message, string[] Categories);
