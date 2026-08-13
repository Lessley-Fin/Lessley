using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Models.Auth;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Options;

namespace Lessley.Gateway.Api.Services.Classes;

public class LoginOtpService : ILoginOtpService
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IVerificationCodeService _codes;
    private readonly IVerificationCodeRepository _codeRepository;
    private readonly IEmailSender _email;
    private readonly IAuthSessionService _sessions;
    private readonly VerificationConfig _config;
    private readonly ILogger<LoginOtpService> _logger;

    // Identical for every address, so requesting a code cannot be used to test who has an account.
    private static readonly object AcknowledgedPayload =
        new { message = "If that email has an account, a sign-in code is on its way." };

    public LoginOtpService(
        UserManager<ApplicationUser> userManager,
        IVerificationCodeService codes,
        IVerificationCodeRepository codeRepository,
        IEmailSender email,
        IAuthSessionService sessions,
        IOptions<VerificationConfig> config,
        ILogger<LoginOtpService> logger)
    {
        _userManager    = userManager;
        _codes          = codes;
        _codeRepository = codeRepository;
        _email          = email;
        _sessions       = sessions;
        _config         = config.Value;
        _logger         = logger;
    }

    public async Task<AuthOperationResult> RequestAsync(RequestLoginCodeDto dto, CancellationToken ct = default)
    {
        var email = dto.Email.Trim();
        var user  = await _userManager.FindByEmailAsync(email);

        if (user is null)
        {
            _logger.LogInformation("Login code requested for an address with no account.");
            return AuthOperationResult.Ok(AcknowledgedPayload);
        }

        // A locked-out account must not be reachable by emailing yourself past the password.
        if (await _userManager.IsLockedOutAsync(user))
            return AuthOperationResult.Invalid(
                "Account temporarily locked due to repeated failed logins. Try again later.");

        var normalizedEmail = _userManager.NormalizeEmail(email) ?? email.ToUpperInvariant();
        var issued = await _codes.IssueAsync(VerificationPurpose.LoginOtp, normalizedEmail, user.Id, ct);

        if (!issued.Issued)
            return AuthOperationResult.Throttled(issued.ThrottleMessage!);

        await _email.SendAsync(
            AuthEmailTemplates.LoginCode(user.Email!, issued.Code!, _config.CodeTtlMinutes), ct);

        return AuthOperationResult.Ok(AcknowledgedPayload);
    }

    public async Task<AuthOperationResult> VerifyAsync(VerifyLoginCodeDto dto, CancellationToken ct = default)
    {
        var email           = dto.Email.Trim();
        var normalizedEmail = _userManager.NormalizeEmail(email) ?? email.ToUpperInvariant();

        var redemption = await _codes.RedeemAsync(VerificationPurpose.LoginOtp, normalizedEmail, dto.Code, ct);
        if (!redemption.Success)
            return AuthOperationResult.Invalid(redemption.FailureMessage!);

        var entry = redemption.Entry!;
        var user  = await _userManager.FindByIdAsync(entry.UserId);

        if (user is null)
        {
            await _codeRepository.DeleteAsync(entry, ct);
            return AuthOperationResult.Invalid("That code is invalid or has expired.");
        }

        if (await _userManager.IsLockedOutAsync(user))
            return AuthOperationResult.Invalid(
                "Account temporarily locked due to repeated failed logins. Try again later.");

        // Single use — the code dies with the session it created.
        await _codeRepository.DeleteAsync(entry, ct);

        // Signing in successfully clears the failed-password counter, matching what a correct
        // password would do.
        await _userManager.ResetAccessFailedCountAsync(user);

        _logger.LogInformation("Passwordless sign-in completed for user {UserId}.", user.Id);

        return AuthOperationResult.WithSession(await _sessions.IssueAsync(user, ct));
    }
}
