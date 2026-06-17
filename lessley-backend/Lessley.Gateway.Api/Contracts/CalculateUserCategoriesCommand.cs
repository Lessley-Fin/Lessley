namespace Lessley.Gateway.Api.Contracts;

public record CalculateUserCategoriesCommand(string UserId, bool TimeFilter = false, int Days = 90, bool UseMock = false);
