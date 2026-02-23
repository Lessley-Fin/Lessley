namespace Lessley.Gateway.Api.Contracts
{
    public class AccessTokenResponse
    {
        public string TokenType { get; set; } = "";
        public int ExpiresIn { get; set; }
        public string AccessToken { get; set; } = "";
    }
}
