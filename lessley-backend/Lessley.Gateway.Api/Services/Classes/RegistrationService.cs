using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Models.Auth;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Options;

namespace Lessley.Gateway.Api.Services.Classes;

public class RegistrationService : IRegistrationService
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IPendingRegistrationRepository _pending;
    private readonly IVerificationCodeService _codes;
    private readonly IEmailSender _email;
    private readonly IAuthSessionService _sessions;
    private readonly VerificationConfig _config;
    private readonly ILogger<RegistrationService> _logger;

    public RegistrationService(
        UserManager<ApplicationUser> userManager,
        IPendingRegistrationRepository pending,
        IVerificationCodeService codes,
        IEmailSender email,
        IAuthSessionService sessions,
        IOptions<VerificationConfig> config,
        ILogger<RegistrationService> logger)
    {
        _userManager = userManager;
        _pending     = pending;
        _codes       = codes;
        _email       = email;
        _sessions    = sessions;
        _config      = config.Value;
        _logger      = logger;
    }

    public async Task<AuthOperationResult> StartAsync(StartRegistrationDto dto, CancellationToken ct = default)
    {
        var email    = dto.Email.Trim();
        var userName = dto.UserName.Trim();

        var normalizedEmail    = _userManager.NormalizeEmail(email) ?? email.ToUpperInvariant();
        var normalizedUserName = _userManager.NormalizeName(userName) ?? userName.ToUpperInvariant();

        // Taken-ness is reported plainly rather than hidden. Registration cannot avoid revealing
        // it — the account either can or cannot be created — and a vague error here only strands
        // a legitimate user who forgot they had signed up.
        if (await _userManager.FindByEmailAsync(email) is not null)
            return AuthOperationResult.Invalid("An account with this email already exists.");

        if (await _userManager.FindByNameAsync(userName) is not null)
            return AuthOperationResult.Invalid("This username is already taken.");

        // Run Identity's own password policy now, at the step where the user typed the password,
        // instead of failing them three steps later at account creation.
        var candidate = new ApplicationUser { UserName = userName, Email = email };
        foreach (var validator in _userManager.PasswordValidators)
        {
            var validation = await validator.ValidateAsync(_userManager, candidate, dto.Password);
            if (!validation.Succeeded)
                return AuthOperationResult.Invalid(
                    string.Join(" ", validation.Errors.Select(e => e.Description)));
        }

        // Starting again wipes whatever was in flight for this address or username, so a
        // half-finished attempt can never be resumed — it is replaced.
        await _pending.DeleteByEmailOrUserNameAsync(normalizedEmail, normalizedUserName, ct);

        var code  = _codes.GenerateCode();
        var token = _codes.GenerateTicket();
        var now   = DateTime.UtcNow;

        var registration = new PendingRegistration
        {
            TokenHash          = _codes.Hash(token),
            UserName           = userName,
            NormalizedUserName = normalizedUserName,
            Email              = email,
            NormalizedEmail    = normalizedEmail,
            // Hashed with the same hasher the real user will use, so the plaintext never rests
            // here and the hash carries over verbatim when the account is finally created.
            PasswordHash       = _userManager.PasswordHasher.HashPassword(candidate, dto.Password),
            CodeHash           = _codes.Hash(code),
            CodeExpiresAt      = now.AddMinutes(_config.CodeTtlMinutes),
            SendCount          = 1,
            LastSentAt         = now,
            CreatedAt          = now,
            ExpiresAt          = now.AddMinutes(_config.PendingRegistrationTtlMinutes),
        };

        await _pending.AddAsync(registration, ct);
        await _email.SendAsync(AuthEmailTemplates.RegistrationCode(email, code, _config.CodeTtlMinutes), ct);

        _logger.LogInformation("Registration started for {UserName}; verification code emailed.", userName);

        return AuthOperationResult.Ok(new
        {
            registrationToken = token,
            email,
            codeExpiresAt     = registration.CodeExpiresAt,
            expiresAt         = registration.ExpiresAt,
            policy            = _codes.Policy,
        });
    }

    public async Task<AuthOperationResult> VerifyEmailAsync(VerifyRegistrationDto dto, CancellationToken ct = default)
    {
        var registration = await _pending.GetByTokenHashAsync(_codes.Hash(dto.RegistrationToken), ct);

        if (registration is null || registration.IsExpired)
            return await RestartAsync(registration, ct);

        if (registration.EmailVerified)
            return AuthOperationResult.Ok(new { verified = true, email = registration.Email });

        if (registration.IsCodeExpired)
            return AuthOperationResult.Invalid("This code has expired. Request a new one.");

        if (!_codes.Verify(dto.Code, registration.CodeHash))
        {
            registration.Attempts++;

            // Out of guesses: drop the whole registration rather than just the code, so the only
            // way forward is to start over from step one.
            if (registration.Attempts >= _config.MaxAttempts)
            {
                await _pending.DeleteAsync(registration, ct);
                return AuthOperationResult.Invalid(
                    "Too many incorrect codes. Start the registration again.");
            }

            await _pending.UpdateAsync(registration, ct);
            return AuthOperationResult.Invalid("That code is not correct.");
        }

        registration.EmailVerified = true;
        registration.Attempts      = 0;
        // Burn the code — verification has already been banked on the document.
        registration.CodeHash      = string.Empty;
        await _pending.UpdateAsync(registration, ct);

        return AuthOperationResult.Ok(new { verified = true, email = registration.Email });
    }

    public async Task<AuthOperationResult> ResendCodeAsync(ResendRegistrationCodeDto dto, CancellationToken ct = default)
    {
        var registration = await _pending.GetByTokenHashAsync(_codes.Hash(dto.RegistrationToken), ct);

        if (registration is null || registration.IsExpired)
            return await RestartAsync(registration, ct);

        if (registration.EmailVerified)
            return AuthOperationResult.Invalid("This email is already verified.");

        var now = DateTime.UtcNow;
        var secondsSinceLast = (now - registration.LastSentAt).TotalSeconds;
        if (secondsSinceLast < _config.ResendCooldownSeconds)
            return AuthOperationResult.Throttled(
                $"Please wait {Math.Ceiling(_config.ResendCooldownSeconds - secondsSinceLast)} seconds before requesting another code.");

        if (registration.SendCount >= _config.MaxResends)
        {
            await _pending.DeleteAsync(registration, ct);
            return AuthOperationResult.Invalid(
                "Too many codes requested. Start the registration again.");
        }

        var code = _codes.GenerateCode();
        registration.CodeHash      = _codes.Hash(code);
        registration.CodeExpiresAt = now.AddMinutes(_config.CodeTtlMinutes);
        registration.Attempts      = 0;
        registration.SendCount++;
        registration.LastSentAt    = now;

        await _pending.UpdateAsync(registration, ct);
        await _email.SendAsync(
            AuthEmailTemplates.RegistrationCode(registration.Email, code, _config.CodeTtlMinutes), ct);

        return AuthOperationResult.Ok(new
        {
            codeExpiresAt = registration.CodeExpiresAt,
            policy        = _codes.Policy,
        });
    }

    public async Task<AuthOperationResult> CompleteAsync(CompleteRegistrationDto dto, CancellationToken ct = default)
    {
        var registration = await _pending.GetByTokenHashAsync(_codes.Hash(dto.RegistrationToken), ct);

        if (registration is null || registration.IsExpired)
            return await RestartAsync(registration, ct);

        if (!registration.EmailVerified)
            return AuthOperationResult.Invalid("Verify your email address before finishing registration.");

        // The address or username may have been claimed by someone else while this registration
        // sat in the wizard.
        if (await _userManager.FindByEmailAsync(registration.Email) is not null ||
            await _userManager.FindByNameAsync(registration.UserName) is not null)
        {
            await _pending.DeleteAsync(registration, ct);
            return AuthOperationResult.Invalid(
                "That email or username was taken while you were registering. Please start again.");
        }

        var user = new ApplicationUser
        {
            UserName      = registration.UserName,
            Email         = registration.Email,
            // The whole point of the flow: the address is proven before the account exists.
            EmailConfirmed = true,
            Clubs         = dto.Clubs,
            MutedTags     = dto.MutedCategories,
            MatchingScore = dto.MatchLevel?.ToMatchingScore() ?? registration.MatchingScore,
            // Carried over from the pending document — the password was never stored in the clear.
            PasswordHash  = registration.PasswordHash,
        };

        var created = await _userManager.CreateAsync(user);
        if (!created.Succeeded)
            return AuthOperationResult.Invalid(
                string.Join(" ", created.Errors.Select(e => e.Description)));

        var roleAssigned = await _userManager.AddToRoleAsync(user, UserRoles.Viewer.ToString());
        if (!roleAssigned.Succeeded)
        {
            // A user with no role would be half-created and unusable; unwind rather than leave it.
            await _userManager.DeleteAsync(user);
            return AuthOperationResult.Invalid(
                string.Join(" ", roleAssigned.Errors.Select(e => e.Description)));
        }

        await _pending.DeleteAsync(registration, ct);

        _logger.LogInformation("Registration completed for {UserName}.", user.UserName);

        return AuthOperationResult.WithSession(await _sessions.IssueAsync(user, ct));
    }

    // Shared exit for "the pending registration is gone or timed out". Also clears the stale
    // document if one is still sitting there past its expiry — Mongo's TTL monitor only sweeps
    // about once a minute, so expiry is enforced here rather than waited on.
    private async Task<AuthOperationResult> RestartAsync(PendingRegistration? expired, CancellationToken ct)
    {
        if (expired is not null)
            await _pending.DeleteAsync(expired, ct);

        return AuthOperationResult.Invalid(
            "This registration has expired or was not found. Please start again.");
    }
}
