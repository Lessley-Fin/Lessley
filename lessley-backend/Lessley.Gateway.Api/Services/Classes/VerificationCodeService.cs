using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.Extensions.Options;
using System.Security.Cryptography;
using System.Text;

namespace Lessley.Gateway.Api.Services.Classes;

public class VerificationCodeService : IVerificationCodeService
{
    private readonly IVerificationCodeRepository _repository;
    private readonly VerificationConfig _config;
    private readonly byte[] _hashKey;

    public VerificationCodeService(
        IVerificationCodeRepository repository,
        IOptions<VerificationConfig> config,
        IOptions<JwtConfig> jwtConfig)
    {
        _repository = repository;
        _config     = config.Value;

        // Keyed with the JWT signing secret rather than adding another secret to deploy. The key
        // matters: a 6-digit code has only a million possibilities, so a plain SHA-256 digest in a
        // leaked database would fall to an instant lookup table. HMAC makes the stored hash
        // useless without the server key.
        _hashKey = Encoding.UTF8.GetBytes(jwtConfig.Value.Key);
    }

    public string GenerateCode()
    {
        var digits = new char[_config.CodeLength];
        for (var i = 0; i < digits.Length; i++)
            digits[i] = (char)('0' + RandomNumberGenerator.GetInt32(10));

        return new string(digits);
    }

    public string GenerateTicket() => Convert.ToHexString(RandomNumberGenerator.GetBytes(32));

    public string Hash(string value)
        => Convert.ToBase64String(HMACSHA256.HashData(_hashKey, Encoding.UTF8.GetBytes(value)));

    public bool Verify(string value, string? storedHash)
    {
        if (string.IsNullOrEmpty(storedHash) || string.IsNullOrEmpty(value))
            return false;

        return CryptographicOperations.FixedTimeEquals(
            Encoding.UTF8.GetBytes(Hash(value)),
            Encoding.UTF8.GetBytes(storedHash));
    }

    public async Task<CodeIssueOutcome> IssueAsync(
        VerificationPurpose purpose, string normalizedEmail, string userId, CancellationToken ct = default)
    {
        var now      = DateTime.UtcNow;
        var existing = await _repository.GetAsync(purpose, normalizedEmail, ct);
        var code     = GenerateCode();

        if (existing is null)
        {
            await _repository.AddAsync(new VerificationCode
            {
                Purpose         = purpose.ToString(),
                NormalizedEmail = normalizedEmail,
                UserId          = userId,
                CodeHash        = Hash(code),
                CodeExpiresAt   = now.AddMinutes(_config.CodeTtlMinutes),
                SendCount       = 1,
                LastSentAt      = now,
                CreatedAt       = now,
                ExpiresAt       = now.AddMinutes(_config.CodeTtlMinutes),
            }, ct);

            return new CodeIssueOutcome(true, code, null);
        }

        var secondsSinceLast = (now - existing.LastSentAt).TotalSeconds;
        if (secondsSinceLast < _config.ResendCooldownSeconds)
        {
            var wait = Math.Ceiling(_config.ResendCooldownSeconds - secondsSinceLast);
            return new CodeIssueOutcome(false, null, $"Please wait {wait} seconds before requesting another code.");
        }

        // A stale burst of requests shouldn't let someone farm codes indefinitely. The window
        // resets naturally once the document TTLs away.
        if (existing.SendCount >= _config.MaxResends)
            return new CodeIssueOutcome(false, null, "Too many codes requested. Please try again later.");

        existing.UserId          = userId;
        existing.CodeHash        = Hash(code);
        existing.CodeExpiresAt   = now.AddMinutes(_config.CodeTtlMinutes);
        existing.ExpiresAt       = now.AddMinutes(_config.CodeTtlMinutes);
        existing.Attempts        = 0;
        existing.SendCount++;
        existing.LastSentAt      = now;
        // A newly issued code invalidates any ticket earned from the previous one.
        existing.TicketHash      = null;
        existing.TicketExpiresAt = null;

        await _repository.UpdateAsync(existing, ct);
        return new CodeIssueOutcome(true, code, null);
    }

    public async Task<CodeRedemption> RedeemAsync(
        VerificationPurpose purpose, string normalizedEmail, string code, CancellationToken ct = default)
    {
        var entry = await _repository.GetAsync(purpose, normalizedEmail, ct);

        // Same wording whether no code was ever requested or the code is simply wrong, so the
        // response cannot be used to probe which addresses have accounts.
        if (entry is null || entry.IsCodeExpired)
            return new CodeRedemption(false, null, "That code is invalid or has expired.");

        if (!Verify(code, entry.CodeHash))
        {
            entry.Attempts++;

            if (entry.Attempts >= _config.MaxAttempts)
            {
                await _repository.DeleteAsync(entry, ct);
                return new CodeRedemption(false, null, "Too many incorrect codes. Request a new one.");
            }

            await _repository.UpdateAsync(entry, ct);
            return new CodeRedemption(false, null, "That code is invalid or has expired.");
        }

        return new CodeRedemption(true, entry, null);
    }
}
