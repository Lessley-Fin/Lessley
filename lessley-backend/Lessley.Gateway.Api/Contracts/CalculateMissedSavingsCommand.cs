namespace Lessley.Gateway.Api.Contracts;

public record CalculateMissedSavingsCommand(string UserId, bool TimeFilter = false, int Days = 90);
