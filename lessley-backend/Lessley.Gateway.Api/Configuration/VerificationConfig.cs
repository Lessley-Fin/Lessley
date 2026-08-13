namespace Lessley.Gateway.Api.Configuration
{
    /// <summary>
    /// Shared knobs for every emailed one-time code: registration email verification,
    /// password reset, and passwordless login.
    /// </summary>
    public class VerificationConfig
    {
        /// <summary>Digits in the emailed code. Six is the ceiling users will retype reliably.</summary>
        public int CodeLength { get; set; } = 6;

        public int CodeTtlMinutes { get; set; } = 10;

        /// <summary>
        /// Wrong guesses allowed before the code is burned. With a 6-digit code this caps the
        /// attacker at 5/1,000,000 per issued code.
        /// </summary>
        public int MaxAttempts { get; set; } = 5;

        /// <summary>Minimum gap between two "send me another code" requests for one address.</summary>
        public int ResendCooldownSeconds { get; set; } = 60;

        /// <summary>Total codes that may be sent for a single pending flow before it must be restarted.</summary>
        public int MaxResends { get; set; } = 5;

        /// <summary>
        /// How long an unfinished registration survives. Past this the pending document is
        /// dropped by the Mongo TTL index and the user starts over from step one.
        /// </summary>
        public int PendingRegistrationTtlMinutes { get; set; } = 30;

        /// <summary>Lifetime of the one-time ticket handed out after a reset code is verified.</summary>
        public int ResetTicketTtlMinutes { get; set; } = 10;
    }
}
