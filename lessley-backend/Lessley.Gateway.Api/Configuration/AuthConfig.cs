namespace Lessley.Gateway.Api.Configuration
{
    public class AuthConfig
    {
        public bool IsRotateRefresh { get; set; } = false;

        public int RefreshTimeoutHours { get; set; } = 12;

        public int AccessTimeoutHours { get; set; } = 2;

        public AuthConfig() { }
    }
}
