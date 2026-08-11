using System.ComponentModel.DataAnnotations;

namespace Lessley.Gateway.Api.Models.Optimizer;

/// <summary>
/// A cart to price against the deals available at one store. Mirrors the
/// deal-optimizer service's own request model; property names are serialized
/// to snake_case on the way out (see <c>OptimizerProxyService</c>).
/// </summary>
public record OptimizeRequestDto
{
    /// <summary>Canonical store the cart is being priced for.</summary>
    [Required]
    public string StoreId { get; init; } = string.Empty;

    /// <summary>Total cart value in ILS.</summary>
    [Range(0.01, double.MaxValue, ErrorMessage = "cartTotal must be greater than 0.")]
    public double CartTotal { get; init; }

    /// <summary>Number of items in the cart.</summary>
    [Range(1, int.MaxValue)]
    public int CartQuantity { get; init; } = 1;

    /// <summary>How many ranked options to return.</summary>
    [Range(1, 20)]
    public int TopN { get; init; } = 5;

    /// <summary>
    /// Longest combination to search for — the most deals one ranked option may
    /// stack. Keeps results realistically executable at a checkout instead of
    /// chasing the last shekel across seven coupons.
    /// </summary>
    [Range(1, 10)]
    public int MaxDeals { get; init; } = 3;

    /// <summary>Treat combinability "unknown" as "no" instead of the optimistic "yes".</summary>
    public bool Strict { get; init; }

    /// <summary>
    /// source_ids the user has access to — loyalty programs joined and cards held.
    /// Server-populated from the caller's saved clubs; anything a client sends here
    /// is discarded. Always serialized (empty list included, never null) so the
    /// optimizer prunes on it rather than treating the caller as an unknown user.
    /// </summary>
    public List<string> MemberSourceIds { get; init; } = [];

    /// <summary>Preferred store types: outlets | online | physical.</summary>
    public List<string> PreferredStoreTypes { get; init; } = [];

    /// <summary>deal_id → times already used this month, for monthly-cap pruning.</summary>
    public Dictionary<string, int> UsesThisMonth { get; init; } = [];
}
