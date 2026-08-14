using Lessley.Gateway.Api.Enums;
using System.ComponentModel.DataAnnotations;

namespace Lessley.Gateway.Api.Models.Auth;

/// <summary>Step 1 — credentials only. Creates a pending registration, not a user.</summary>
public class StartRegistrationDto
{
    [Required]
    [StringLength(256, MinimumLength = 3)]
    public string UserName { get; set; } = string.Empty;

    [Required]
    [EmailAddress]
    [StringLength(320)]
    public string Email { get; set; } = string.Empty;

    [Required]
    [StringLength(128, MinimumLength = 8)]
    public string Password { get; set; } = string.Empty;
}

/// <summary>Step 2 — proves the mailbox belongs to whoever started the registration.</summary>
public class VerifyRegistrationDto
{
    [Required]
    public string RegistrationToken { get; set; } = string.Empty;

    [Required]
    [StringLength(12, MinimumLength = 4)]
    public string Code { get; set; } = string.Empty;
}

public class ResendRegistrationCodeDto
{
    [Required]
    public string RegistrationToken { get; set; } = string.Empty;
}

/// <summary>
/// Final step — the only call that creates an <c>ApplicationUser</c>. Carries the preferences
/// gathered by the later wizard steps.
/// </summary>
public class CompleteRegistrationDto
{
    [Required]
    public string RegistrationToken { get; set; } = string.Empty;

    public List<string> Clubs { get; set; } = new();

    public MatchLevel? MatchLevel { get; set; }

    public List<string> MutedCategories { get; set; } = new();
}
