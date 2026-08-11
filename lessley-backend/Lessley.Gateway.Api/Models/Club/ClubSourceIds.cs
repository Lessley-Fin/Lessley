namespace Lessley.Gateway.Api.Models.Club;

/// <summary>
/// Translates the club ids stored on a user (<c>club_hot</c>) into the
/// <c>source_id</c>s the deal side keys on (<c>hot</c>).
/// </summary>
/// <remarks>
/// Every club in the seed definitions (<c>lessley-deals/data/seed/clubs.json</c>) is
/// named <c>club_</c> + its own <c>source_id</c>, so this is a prefix strip rather
/// than a lookup against <c>club_list</c> — one less collection read per optimize.
/// The convention is hand-maintained, not derived, which is why
/// <c>ClubSourceIdsTests</c> pins it: a club that breaks it would silently prune
/// the deals its own members are entitled to.
/// </remarks>
public static class ClubSourceIds
{
    private const string Prefix = "club_";

    /// <summary>Maps club ids to source_ids. A bare source_id passes through unchanged.</summary>
    public static List<string> FromClubIds(IEnumerable<string>? clubIds) =>
        (clubIds ?? [])
            .Where(id => !string.IsNullOrWhiteSpace(id))
            .Select(id => id.Trim())
            .Select(id => id.StartsWith(Prefix, StringComparison.Ordinal) ? id[Prefix.Length..] : id)
            .Where(id => id.Length > 0)
            .Distinct(StringComparer.Ordinal)
            .ToList();
}
