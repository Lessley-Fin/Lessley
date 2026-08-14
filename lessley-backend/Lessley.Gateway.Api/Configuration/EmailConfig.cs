namespace Lessley.Gateway.Api.Configuration
{
    /// <summary>SMTP settings for the transactional auth emails (verification, reset, login codes).</summary>
    public class EmailConfig
    {
        /// <summary>
        /// When false the Gateway does not talk to an SMTP server at all and every message is
        /// written to the log instead. Left false by default so a fresh checkout boots without
        /// credentials; production must set it to true.
        /// </summary>
        public bool Enabled { get; set; } = false;

        public string Host { get; set; } = string.Empty;

        public int Port { get; set; } = 587;

        /// <summary>
        /// STARTTLS on the submission port (587). Set false only for port 465, which is
        /// implicit TLS and is detected from the port number.
        /// </summary>
        public bool UseStartTls { get; set; } = true;

        public string UserName { get; set; } = string.Empty;

        public string Password { get; set; } = string.Empty;

        public string FromAddress { get; set; } = string.Empty;

        public string FromName { get; set; } = "Lessley";

        /// <summary>Public base URL of the app, used to build links inside the emails.</summary>
        public string AppUrl { get; set; } = string.Empty;

        /// <summary>Give up rather than hanging a request thread on an unreachable SMTP host.</summary>
        public int TimeoutSeconds { get; set; } = 15;
    }
}
