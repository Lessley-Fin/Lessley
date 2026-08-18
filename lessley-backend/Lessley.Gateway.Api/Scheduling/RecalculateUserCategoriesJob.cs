using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Quartz;

namespace Lessley.Gateway.Api.Scheduling;

/// <summary>
/// Asks Personalization to recalculate every user's spending categories.
/// </summary>
/// <remarks>
/// The three event triggers — registration, bank journey, match-level change — all fire when
/// a user's *configuration* changes. None of them fires when their *spending* changes, which
/// it does continuously. Without this sweep a user who signs up, links a bank and never
/// revisits their settings would keep the categories computed on day one forever.
///
/// It also covers everyone who predates the command path, which is why it replaced a one-off
/// backfill: standing infrastructure rather than a migration someone has to remember to run.
/// </remarks>
[DisallowConcurrentExecution]
public class RecalculateUserCategoriesJob : IJob
{
    private readonly IServiceScopeFactory _scopes;
    private readonly ILogger<RecalculateUserCategoriesJob> _logger;

    public RecalculateUserCategoriesJob(
        IServiceScopeFactory scopes,
        ILogger<RecalculateUserCategoriesJob> logger)
    {
        _scopes = scopes;
        _logger = logger;
    }

    public async Task Execute(IJobExecutionContext context)
    {
        var ct = context.CancellationToken;

        // The job itself is a singleton; UserManager and the publisher are scoped.
        using var scope = _scopes.CreateScope();
        var userManager     = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var personalization = scope.ServiceProvider.GetRequiredService<IPersonalizationService>();

        var emails = await userManager.Users
            .Where(u => u.Email != null)
            .Select(u => u.Email!)
            .ToListAsync(ct);

        _logger.LogInformation("Category sweep starting for {Count} user(s)", emails.Count);

        // The trigger swallows publish failures (see PersonalizationService), so a broker
        // hiccup costs one user's refresh rather than stranding everyone after them in the
        // list. Consumption is bounded on the far side — Personalization takes these ten at a
        // time — so the queue absorbs the burst rather than Open Finance.
        var published = 0;
        foreach (var email in emails)
        {
            ct.ThrowIfCancellationRequested();
            await personalization.TriggerCalculateUserCategoriesAsync(email, ct: ct);
            published++;
        }

        _logger.LogInformation("Category sweep published {Published} of {Count} command(s)", published, emails.Count);
    }
}
