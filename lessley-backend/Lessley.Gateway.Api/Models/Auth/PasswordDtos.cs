using System.ComponentModel.DataAnnotations;

namespace Lessley.Gateway.Api.Models.Auth;

/// <summary>Step 1 — asks for a reset code. Always answered identically, account or not.</summary>
public class ForgotPasswordDto
{
    [Required]
    [EmailAddress]
    [StringLength(320)]
    public string Email { get; set; } = string.Empty;
}

/// <summary>Step 2 — trades a valid code for a single-use reset ticket.</summary>
public class VerifyPasswordResetCodeDto
{
    [Required]
    [EmailAddress]
    [StringLength(320)]
    public string Email { get; set; } = string.Empty;

    [Required]
    [StringLength(12, MinimumLength = 4)]
    public string Code { get; set; } = string.Empty;
}

/// <summary>Step 3 — sets the new password against the ticket from step 2.</summary>
public class ResetPasswordDto
{
    [Required]
    [EmailAddress]
    [StringLength(320)]
    public string Email { get; set; } = string.Empty;

    [Required]
    public string ResetTicket { get; set; } = string.Empty;

    [Required]
    [StringLength(128, MinimumLength = 8)]
    public string NewPassword { get; set; } = string.Empty;
}
