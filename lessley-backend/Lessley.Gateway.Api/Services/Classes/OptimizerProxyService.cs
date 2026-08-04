using Lessley.Gateway.Api.Models.Optimizer;
using Lessley.Gateway.Api.Services.Interfaces;
using System.Net.Http.Json;
using System.Text.Json;

namespace Lessley.Gateway.Api.Services.Classes;

/// <summary>
/// Talks to the deal-optimizer service. The optimizer speaks snake_case, so the
/// request is serialized with a snake_case naming policy rather than having the
/// DTO carry a JsonPropertyName on every property.
/// </summary>
public class OptimizerProxyService : IOptimizerProxyService
{
    private static readonly JsonSerializerOptions SnakeCase = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    };

    private readonly HttpClient _httpClient;

    public OptimizerProxyService(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    public Task<HttpResponseMessage> OptimizeAsync(OptimizeRequestDto request, CancellationToken ct = default)
        => _httpClient.PostAsJsonAsync("optimize", request, SnakeCase, ct);
}
