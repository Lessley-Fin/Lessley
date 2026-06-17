namespace Lessley.Gateway.Api.Contracts;

public record CalculateTopAccountsCommand(string UserId, bool TimeFilter = false, int Days = 90);
