namespace Lessley.Gateway.Api.Models.Club;

/// <summary>
/// A loyalty club. <paramref name="SourceId"/> is the scraper id deals are tagged with
/// (hot, mastercard, ...), which is what a deal carries instead of the club's own id —
/// so it is the key clients join a deal to its club name on. Null on rows that predate it.
/// </summary>
public record ClubDto(string Id, string Name, string? SourceId);
