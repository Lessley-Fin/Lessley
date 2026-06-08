using Lessley.Gateway.Api.Enums;

namespace Lessley.Gateway.Api.Models
{
    public class RegisterDto
    {
        public string UserName { get; set; } = string.Empty;

        // Email is the system-wide primary identifier and must be linked to Open Finance.
        public string Email { get; set; } = string.Empty;
        public string Password { get; set; } = string.Empty;

        // Loyalty clubs the user belongs to.
        public List<string> Clubs { get; set; } = new();

        // Desired match level (High > 75%, Medium > 50%, Low > 25%). Drives MatchingScore.
        public MatchLevel? MatchLevel { get; set; }

        // Categories to mute, expressed as MCC string labels.
        public List<string> MutedCategories { get; set; } = new();
    }
}
