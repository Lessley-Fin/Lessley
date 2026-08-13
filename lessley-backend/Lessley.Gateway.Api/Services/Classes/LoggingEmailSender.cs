using Lessley.Gateway.Api.Services.Interfaces;

namespace Lessley.Gateway.Api.Services.Classes;

/// <summary>
/// Development fallback used when <c>EmailConfig:Enabled</c> is false: writes the message to the
/// log instead of sending it, so register / reset / OTP-login can be walked end to end locally
/// with no SMTP credentials. Program.cs refuses to select this outside Development.
/// </summary>
public class LoggingEmailSender : IEmailSender
{
    private readonly ILogger<LoggingEmailSender> _logger;

    public LoggingEmailSender(ILogger<LoggingEmailSender> logger) => _logger = logger;

    public Task SendAsync(EmailMessage message, CancellationToken ct = default)
    {
        // The plain-text body is logged in full — that is the entire point of this sender, and it
        // only ever runs in Development.
        _logger.LogWarning(
            "EMAIL NOT SENT (SMTP disabled). To: {Recipient} | Subject: {Subject}\n{Body}",
            message.To, message.Subject, message.TextBody);

        return Task.CompletedTask;
    }
}
