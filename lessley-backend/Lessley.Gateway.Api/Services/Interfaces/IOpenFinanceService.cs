namespace Lessley.Gateway.Api.Services.Interfaces
{
    public interface IOpenFinanceService
    {
        public Task<string> CreateAccessToken(string username);
    }
}