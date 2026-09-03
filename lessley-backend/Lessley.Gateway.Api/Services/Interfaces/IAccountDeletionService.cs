using Lessley.Gateway.Api.Models;

namespace Lessley.Gateway.Api.Services.Interfaces;

/// <summary>
/// The outcome of a self-service account deletion. Wrong identifier and wrong password collapse
/// into one <see cref="InvalidCredentials"/> case on purpose: the caller is already authenticated,
/// so telling them which half they got wrong only helps someone at a borrowed keyboard.
/// </summary>
public abstract record AccountDeletionResult
{
    public static AccountDeletionResult Ok()                          => new Success();
    public static AccountDeletionResult NotFound()                    => new NotFoundResult();
    public static AccountDeletionResult Invalid()                     => new InvalidCredentials();
    public static AccountDeletionResult Locked()                      => new LockedOut();
    public static AccountDeletionResult OpenFinance(string reason)    => new OpenFinanceFailed(reason);

    public sealed record Success                      : AccountDeletionResult;
    public sealed record NotFoundResult               : AccountDeletionResult;
    public sealed record InvalidCredentials           : AccountDeletionResult;
    public sealed record LockedOut                    : AccountDeletionResult;
    public sealed record OpenFinanceFailed(string Reason) : AccountDeletionResult;
}

/// <summary>
/// Deletes a user's own account: re-authenticates them, optionally revokes their Open Finance
/// consent, then removes the account and everything keyed to it.
/// </summary>
public interface IAccountDeletionService
{
    Task<AccountDeletionResult> DeleteAsync(string callerEmail, DeleteAccountDto dto, CancellationToken ct = default);
}
