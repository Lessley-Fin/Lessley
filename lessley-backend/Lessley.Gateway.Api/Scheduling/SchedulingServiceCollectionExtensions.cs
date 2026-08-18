using Quartz;

namespace Lessley.Gateway.Api.Scheduling;

/// <summary>
/// Cron-scheduled background work. Add a job here and it is scheduled; there is deliberately
/// no other place a recurring task can be started from.
/// </summary>
public static class SchedulingServiceCollectionExtensions
{
    public static IServiceCollection AddScheduledJobs(
        this IServiceCollection services,
        IConfiguration configuration,
        IWebHostEnvironment environment)
    {
        // Tests drive the pieces directly and must not have a scheduler firing underneath them.
        if (environment.IsEnvironment("Testing"))
            return services;

        services.AddQuartz(quartz =>
        {
            AddCronJob<RecalculateUserCategoriesJob>(quartz, configuration,
                name: "recalculate-user-categories",
                defaultCron: "0 0 0 ? * MON");
        });

        // Let an in-flight sweep finish rather than tearing it down mid-publish on shutdown.
        services.AddQuartzHostedService(options => options.WaitForJobsToComplete = true);

        return services;
    }

    /// <summary>
    /// Schedules one job. The cron lives in configuration under <c>Scheduling:{name}</c>, so a
    /// schedule can be changed — or the job switched off with an empty value — without a deploy.
    /// </summary>
    /// <remarks>
    /// Every schedule is UTC. Quartz resolves cron against a time zone, and defaulting to the
    /// host's would make "Monday midnight" mean different instants on different machines and
    /// shift twice a year under DST.
    /// </remarks>
    private static void AddCronJob<TJob>(
        IServiceCollectionQuartzConfigurator quartz,
        IConfiguration configuration,
        string name,
        string defaultCron) where TJob : IJob
    {
        var cron = configuration[$"Scheduling:{name}"] ?? defaultCron;
        if (string.IsNullOrWhiteSpace(cron))
            return;

        var key = new JobKey(name);

        quartz.AddJob<TJob>(job => job.WithIdentity(key));
        quartz.AddTrigger(trigger => trigger
            .ForJob(key)
            .WithIdentity($"{name}-trigger")
            .WithCronSchedule(cron, schedule => schedule
                .InTimeZone(TimeZoneInfo.Utc)
                // A host that was down at the scheduled instant runs the job once on return
                // rather than skipping the week entirely.
                .WithMisfireHandlingInstructionFireAndProceed()));
    }
}
