using System.Text.Json;

namespace Lessley.Gateway.Api.Contracts;

public record MissedSavingsCalculatedEvent(string UserId, DateTime CalculatedAt, JsonElement? Data);
