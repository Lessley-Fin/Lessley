namespace Lessley.Gateway.Api.Contracts;

public record CalculateMissedSavingsCommand(string UserId, bool TimeFilter = true, int Days = 7);
