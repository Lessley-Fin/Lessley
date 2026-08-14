using System.ComponentModel.DataAnnotations;

namespace Lessley.Gateway.Api.Models.Auth;

/// <summary>Asks for a sign-in code. Answered identically whether or not the address has an account.</summary>
public class RequestLoginCodeDto
{
    [Required]
    [EmailAddress]
    [StringLength(320)]
    public string Email { get; set; } = string.Empty;
}

/// <summary>Redeems a sign-in code for a session — no password involved.</summary>
public class VerifyLoginCodeDto
{
    [Required]
    [EmailAddress]
    [StringLength(320)]
    public string Email { get; set; } = string.Empty;

    [Required]
    [StringLength(12, MinimumLength = 4)]
    public string Code { get; set; } = string.Empty;
}
