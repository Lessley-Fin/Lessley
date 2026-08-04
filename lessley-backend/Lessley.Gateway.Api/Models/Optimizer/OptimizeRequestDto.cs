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

    /// <summary>Treat combinability "unknown" as "no" instead of the optimistic "yes".</summary>
    public bool Strict { get; init; }

    /// <summary>source_ids the user has access to — loyalty programs joined and cards held.</summary>
    public List<string> MemberSourceIds { get; init; } = [];

    /// <summary>Preferred store types: outlets | online | physical.</summary>
    public List<string> PreferredStoreTypes { get; init; } = [];

    /// <summary>deal_id → times already used this month, for monthly-cap pruning.</summary>
    public Dictionary<string, int> UsesThisMonth { get; init; } = [];
}
