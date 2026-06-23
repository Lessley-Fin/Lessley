namespace Lessley.Gateway.Api.Models;

// Tags are intentionally excluded — use PUT /api/user/{id}/tags (Admin only) instead.
public record UpdateUserDto(
    List<string>? MutedTags,
    List<string>? Clubs,
    string? MatchLevel
);
