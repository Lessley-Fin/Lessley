namespace Lessley.Gateway.Api.Enums;

/// <summary>
/// Desired club/category match selectivity chosen at registration.
/// The stored MatchingScore is the fraction of least-relevant categories to drop during
/// recalculation (Process 2): e.g. High drops 75% (keeps the top 25%), Low drops 25%.
/// </summary>
public enum MatchLevel
{
    Low,    // > 25%
    Medium, // > 50%
    High,   // > 75%
}

public static class MatchLevelExtensions
{
    public static double ToMatchingScore(this MatchLevel level) => level switch
    {
        MatchLevel.High   => 0.75,
        MatchLevel.Medium => 0.50,
        MatchLevel.Low    => 0.25,
        _                 => 0.25,
    };

    public static MatchLevel? ToMatchLevel(this double? score) => score switch
    {
        0.75 => MatchLevel.High,
        0.50 => MatchLevel.Medium,
        0.25 => MatchLevel.Low,
        _    => null,
    };
}
