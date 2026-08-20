using Microsoft.AspNetCore.Identity;

namespace Lessley.Gateway.Api.Models;

public class ApplicationUser : IdentityUser
{
    public List<string>? Tags { get; set; } = new();
    public List<string>? MutedTags { get; set; } = new();
    public List<string>? Clubs { get; set; } = new();
    public double? MatchingScore { get; set; }
    public bool? WelcomeNotificationSent { get; set; }
}
