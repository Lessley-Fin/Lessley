using Lessley.Gateway.Api.Models.Optimizer;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IOptimizerProxyService
{
    Task<HttpResponseMessage> OptimizeAsync(OptimizeRequestDto request, CancellationToken ct = default);
}
