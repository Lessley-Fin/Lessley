using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;

namespace Lessley.Gateway.Api.Services.Classes;

public class AccountDeletionService : IAccountDeletionService
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly SignInManager<ApplicationUser> _signInManager;
    private readonly IOpenFinanceService _openFinanceService;
    private readonly INotificationRepository _notifications;
    private readonly IAuthSessionService _sessions;
    private readonly IPendingRegistrationRepository _pendingRegistrations;
    private readonly IVerificationCodeRepository _verificationCodes;
    private readonly IConnectionManager _connectionManager;
    private readonly ILogger<AccountDeletionService> _logger;

    public AccountDeletionService(
        UserManager<ApplicationUser> userManager,
        SignInManager<ApplicationUser> signInManager,
        IOpenFinanceService openFinanceService,
        INotificationRepository notifications,
        IAuthSessionService sessions,
        IPendingRegistrationRepository pendingRegistrations,
        IVerificationCodeRepository verificationCodes,
        IConnectionManager connectionManager,
        ILogger<AccountDeletionService> logger)
    {
        _userManager          = userManager;
        _signInManager        = signInManager;
        _openFinanceService   = openFinanceService;
        _notifications        = notifications;
        _sessions             = sessions;
        _pendingRegistrations = pendingRegistrations;
        _verificationCodes    = verificationCodes;
        _connectionManager    = connectionManager;
        _logger               = logger;
    }

    public async Task<AccountDeletionResult> DeleteAsync(
        string callerEmail, DeleteAccountDto dto, CancellationToken ct = default)
    {
        var user = await _userManager.FindByEmailAsync(callerEmail);
        if (user is null)
            return AccountDeletionResult.NotFound();

        // The identifier decides nothing about *who* is deleted — that is the JWT's email, so a
        // caller can only ever delete themselves. It is a deliberate speed bump: typing your own
        // name is what separates "I meant this" from a stray click on someone else's session.
        var identifier = dto.UserNameOrEmail.Trim();
        var identifierMatches =
            string.Equals(identifier, user.UserName, StringComparison.OrdinalIgnoreCase) ||
            string.Equals(identifier, user.Email,    StringComparison.OrdinalIgnoreCase);

        if (!identifierMatches)
        {
            _logger.LogWarning("Account deletion rejected: the identifier did not match the caller");
            return AccountDeletionResult.Invalid();
        }

        // Same check password login runs (AuthController.Login), so these attempts count toward
        // the configured lockout instead of giving this endpoint an unmetered password oracle.
        var signIn = await _signInManager.CheckPasswordSignInAsync(user, dto.Password, lockoutOnFailure: true);
        if (signIn.IsLockedOut)
            return AccountDeletionResult.Locked();
        if (!signIn.Succeeded)
            return AccountDeletionResult.Invalid();

        // Nothing has been deleted yet, and nothing is until the bank consent is settled: a live
        // Open Finance connection must never outlive the only account that could revoke it.
        if (dto.CloseOpenFinanceConnection)
        {
            try
            {
                await _openFinanceService.CloseAllConnectionsAsync(callerEmail, ct);
            }
            catch (Exception ex) when (ex is HttpRequestException or InvalidOperationException or TaskCanceledException)
            {
                _logger.LogError(ex, "Could not close the Open Finance connections; account left intact");
                return AccountDeletionResult.OpenFinance(ex.Message);
            }
        }

        await PurgeUserDataAsync(user, ct);

        var deleted = await _userManager.DeleteAsync(user);
        if (!deleted.Succeeded)
        {
            // Thrown rather than returned: the satellite data is already gone, so this is a
            // half-finished delete the user cannot see or retry into a clean state. It needs a
            // 500 and a log entry, not a tidy result code.
            throw new InvalidOperationException(
                "Failed to delete the user account: " +
                string.Join(" ", deleted.Errors.Select(e => e.Description)));
        }

        _logger.LogInformation(
            "Account deleted (open finance connections closed: {ClosedConnections})",
            dto.CloseOpenFinanceConnection);

        return AccountDeletionResult.Ok();
    }

    /// <summary>
    /// Removes everything keyed to the user that Identity does not cascade. Ordered before the
    /// account itself: writes here are not transactional (AutoTransactionBehavior.Never), and a
    /// failure that leaves a working account is recoverable, while one that leaves rows keyed to
    /// a now-free email is inherited by whoever registers that address next.
    /// </summary>
    private async Task PurgeUserDataAsync(ApplicationUser user, CancellationToken ct)
    {
        var email = user.Email ?? string.Empty;

        // Notifications are keyed by email, refresh tokens by the Identity id. Two different
        // "user id" meanings — using either one for both silently misses a collection.
        await _notifications.DeleteByUserAsync(email, ct);
        await _sessions.DeleteAllRefreshTokensAsync(user.Id, ct);

        await _pendingRegistrations.DeleteByEmailOrUserNameAsync(
            user.NormalizedEmail ?? string.Empty, user.NormalizedUserName ?? string.Empty, ct);
        await _verificationCodes.DeleteByEmailAsync(user.NormalizedEmail ?? string.Empty, ct);

        // Drop the live SignalR sessions so nothing is pushed at an account that no longer
        // exists. Also keyed by email — see EmailUserIdProvider.
        foreach (var connectionId in _connectionManager.GetConnections(email).ToList())
            _connectionManager.RemoveConnection(email, connectionId);
    }
}
