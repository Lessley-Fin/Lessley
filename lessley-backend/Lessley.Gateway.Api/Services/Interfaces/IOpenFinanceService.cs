using Lessley.Gateway.Api.Contracts;

namespace Lessley.Gateway.Api.Services.Interfaces
{
    public interface IOpenFinanceService
    {
        public Task<string> CreateAccessToken(string username);

        public Task<OBTransactionsResponse> GetTransactions(string username);

        public Task<ConnectionResponse> InitiateConnectionJourney(string username, string expiryDate);

    }
}