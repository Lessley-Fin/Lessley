namespace Lessley.Gateway.Api.Models;

public record UpdateUserDto(
    List<string>? Tags,
    List<string>? MutedTags,
    List<string>? Clubs,
    double? MatchingScore
);
