using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Models.Auth;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Options;

namespace Lessley.Gateway.Api.Services.Classes;

public class PasswordResetService : IPasswordResetService
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IVerificationCodeService _codes;
    private readonly IVerificationCodeRepository _codeRepository;
    private readonly IEmailSender _email;
    private readonly IAuthSessionService _sessions;
    private readonly VerificationConfig _config;
    private readonly ILogger<PasswordResetService> _logger;

    // One response for every "forgot password" request, whatever the address. Anything more
    // specific turns this endpoint into an account-enumeration oracle. The policy is static
    // configuration — the same for every caller — so including it keeps the two branches
    // byte-identical while letting the UI state the real expiry instead of guessing.
    private object AcknowledgedPayload => new
    {
        message = "If that email has an account, a reset code is on its way.",
        policy  = _codes.Policy,
    };

    public PasswordResetService(
        UserManager<ApplicationUser> userManager,
        IVerificationCodeService codes,
        IVerificationCodeRepository codeRepository,
        IEmailSender email,
        IAuthSessionService sessions,
        IOptions<VerificationConfig> config,
        ILogger<PasswordResetService> logger)
    {
        _userManager    = userManager;
        _codes          = codes;
        _codeRepository = codeRepository;
        _email          = email;
        _sessions       = sessions;
        _config         = config.Value;
        _logger         = logger;
    }

    public async Task<AuthOperationResult> RequestAsync(ForgotPasswordDto dto, CancellationToken ct = default)
    {
        var email = dto.Email.Trim();
        var user  = await _userManager.FindByEmailAsync(email);

        if (user is null)
        {
            _logger.LogInformation("Password reset requested for an address with no account.");
            return AuthOperationResult.Ok(AcknowledgedPayload);
        }

        var normalizedEmail = _userManager.NormalizeEmail(email) ?? email.ToUpperInvariant();
        var issued = await _codes.IssueAsync(VerificationPurpose.PasswordReset, normalizedEmail, user.Id, ct);

        // Throttling is reported honestly here: the caller already proved nothing by hitting it,
        // since an unknown address never reaches this branch at all.
        if (!issued.Issued)
            return AuthOperationResult.Throttled(issued.ThrottleMessage!);

        await _email.SendAsync(
            AuthEmailTemplates.PasswordResetCode(user.Email!, issued.Code!, _config.CodeTtlMinutes), ct);

        return AuthOperationResult.Ok(AcknowledgedPayload);
    }

    public async Task<AuthOperationResult> VerifyCodeAsync(
        VerifyPasswordResetCodeDto dto, CancellationToken ct = default)
    {
        var email           = dto.Email.Trim();
        var normalizedEmail = _userManager.NormalizeEmail(email) ?? email.ToUpperInvariant();

        var redemption = await _codes.RedeemAsync(VerificationPurpose.PasswordReset, normalizedEmail, dto.Code, ct);
        if (!redemption.Success)
            return AuthOperationResult.Invalid(redemption.FailureMessage!);

        var entry  = redemption.Entry!;
        var ticket = _codes.GenerateTicket();

        // The code is spent here and swapped for a ticket, so the final call carries a
        // high-entropy secret instead of six digits that were sitting in an inbox.
        entry.CodeHash        = string.Empty;
        entry.TicketHash      = _codes.Hash(ticket);
        entry.TicketExpiresAt = DateTime.UtcNow.AddMinutes(_config.ResetTicketTtlMinutes);
        entry.ExpiresAt       = entry.TicketExpiresAt.Value;
        await _codeRepository.UpdateAsync(entry, ct);

        return AuthOperationResult.Ok(new { resetTicket = ticket, expiresAt = entry.TicketExpiresAt });
    }

    public async Task<AuthOperationResult> ResetAsync(ResetPasswordDto dto, CancellationToken ct = default)
    {
        var email           = dto.Email.Trim();
        var normalizedEmail = _userManager.NormalizeEmail(email) ?? email.ToUpperInvariant();

        var entry = await _codeRepository.GetAsync(VerificationPurpose.PasswordReset, normalizedEmail, ct);
        if (entry is null || entry.IsTicketExpired || !_codes.Verify(dto.ResetTicket, entry.TicketHash))
            return AuthOperationResult.Invalid("This reset link has expired. Start the reset again.");

        var user = await _userManager.FindByIdAsync(entry.UserId);
        if (user is null)
        {
            await _codeRepository.DeleteAsync(entry, ct);
            return AuthOperationResult.Invalid("This reset link has expired. Start the reset again.");
        }

        // Identity's own reset token generation + validation, so the password goes through the
        // configured hasher and every registered password validator.
        var resetToken = await _userManager.GeneratePasswordResetTokenAsync(user);
        var result     = await _userManager.ResetPasswordAsync(user, resetToken, dto.NewPassword);

        if (!result.Succeeded)
            return AuthOperationResult.Invalid(string.Join(" ", result.Errors.Select(e => e.Description)));

        // The ticket is single use.
        await _codeRepository.DeleteAsync(entry, ct);

        // Whoever knew the old password is signed out everywhere — that is the point of a reset
        // when the account may already have been taken over.
        await _sessions.RevokeAllRefreshTokensAsync(user.Id, ct);

        // Failed logins before the reset should not keep the rightful owner locked out.
        await _userManager.ResetAccessFailedCountAsync(user);
        await _userManager.SetLockoutEndDateAsync(user, null);

        _logger.LogInformation("Password reset completed for user {UserId}; all sessions revoked.", user.Id);

        return AuthOperationResult.Ok(new { message = "Your password has been changed. You can now sign in." });
    }
}
