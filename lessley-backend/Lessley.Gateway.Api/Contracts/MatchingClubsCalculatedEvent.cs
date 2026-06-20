using System.Text.Json;

namespace Lessley.Gateway.Api.Contracts;

public record MatchingClubsCalculatedEvent(string UserId, DateTime CalculatedAt, JsonElement? Data);
