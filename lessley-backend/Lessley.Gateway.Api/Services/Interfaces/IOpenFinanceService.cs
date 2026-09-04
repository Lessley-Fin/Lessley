using Lessley.Gateway.Api.Contracts;

namespace Lessley.Gateway.Api.Services.Interfaces
{
    public interface IOpenFinanceService
    {
        public Task<string> CreateAccessToken(string username);

        public Task<OBTransactionsResponse> GetTransactions(string username);

        public Task<ConnectionResponse> InitiateConnectionJourney(string username, string? redirectUrl = null);

        /// <summary>Lists the ids of every Open Finance connection the user currently holds.</summary>
        Task<IReadOnlyList<string>> GetConnectionIdsAsync(string username, CancellationToken ct = default);

        /// <summary>
        /// Revokes every Open Finance connection the user holds. Throws if any of them could not
        /// be closed, so a caller deleting an account can abort rather than orphan a live consent.
        /// </summary>
        Task CloseAllConnectionsAsync(string username, CancellationToken ct = default);
    }
}
