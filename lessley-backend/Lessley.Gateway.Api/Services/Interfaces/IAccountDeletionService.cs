namespace Lessley.Gateway.Api.Services.Interfaces;

/// <summary>
/// The outcome of a self-service account deletion. There is no "wrong credentials" case: the
/// caller is identified by their JWT and nothing else, and the confirmation the user types is a
/// client-side speed bump that never reaches the server.
/// </summary>
public abstract record AccountDeletionResult
{
    public static AccountDeletionResult Ok()                          => new Success();
    public static AccountDeletionResult NotFound()                    => new NotFoundResult();
    public static AccountDeletionResult OpenFinance(string reason)    => new OpenFinanceFailed(reason);

    public sealed record Success                      : AccountDeletionResult;
    public sealed record NotFoundResult               : AccountDeletionResult;
    public sealed record OpenFinanceFailed(string Reason) : AccountDeletionResult;
}

/// <summary>
/// Deletes a user's own account: revokes their Open Finance consent, then removes the account and
/// everything keyed to it. Deleting is all-or-nothing — the bank connection always goes with it.
/// </summary>
public interface IAccountDeletionService
{
    Task<AccountDeletionResult> DeleteAsync(string callerEmail, CancellationToken ct = default);
}
