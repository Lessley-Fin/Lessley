using Lessley.Gateway.Api.Services.Interfaces;
using Quartz;

namespace Lessley.Gateway.Api.Scheduling;

/// <summary>
/// Collapses raw engagement events into <c>entity_stats</c>, so the hot feed reads one small
/// pre-scored collection instead of aggregating the event log per request.
/// </summary>
/// <remarks>
/// Nightly rather than on-write because the score is deliberately not real-time: decay is
/// measured in days and the smoothing only means anything once a batch of impressions has
/// accumulated. Re-scoring on every event would burn work to move a number nobody can see.
///
/// Everything is caught and logged. A rollup that throws must cost one night's freshness —
/// the previous scores stay in place and the feed keeps serving — not take the scheduler down.
/// </remarks>
[DisallowConcurrentExecution]
public class HotScoreRollupJob : IJob
{
    private readonly IServiceScopeFactory _scopes;
    private readonly ILogger<HotScoreRollupJob> _logger;

    public HotScoreRollupJob(IServiceScopeFactory scopes, ILogger<HotScoreRollupJob> logger)
    {
        _scopes = scopes;
        _logger = logger;
    }

    public async Task Execute(IJobExecutionContext context)
    {
        // The job is a singleton; the repositories behind IInterestService are scoped.
        using var scope   = _scopes.CreateScope();
        var       service = scope.ServiceProvider.GetRequiredService<IInterestService>();

        try
        {
            await service.RollupAsync(context.CancellationToken);
        }
        catch (OperationCanceledException) when (context.CancellationToken.IsCancellationRequested)
        {
            _logger.LogInformation("Hot-score rollup cancelled during shutdown.");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Hot-score rollup failed; previous scores remain in place.");
        }
    }
}
