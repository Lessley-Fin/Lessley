namespace Lessley.Gateway.Api.Contracts;

public record CalculateTopStoresCommand(string UserId, bool TimeFilter = false, int Days = 90);
