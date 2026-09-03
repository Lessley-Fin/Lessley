using System.ComponentModel.DataAnnotations;

namespace Lessley.Gateway.Api.Models;

/// <summary>What the caller must supply to delete their own account.</summary>
/// <remarks>
/// The identifier is confirmation, never identity: who is being deleted comes from the JWT.
/// Typing it is the step that stops a walk-up deletion on an unlocked device.
/// </remarks>
public class DeleteAccountDto
{
    [Required]
    public string UserNameOrEmail { get; set; } = string.Empty;

    [Required]
    public string Password { get; set; } = string.Empty;

    /// <summary>Also revoke the user's Open Finance bank consent, not just the Lessley account.</summary>
    public bool CloseOpenFinanceConnection { get; set; }
}
