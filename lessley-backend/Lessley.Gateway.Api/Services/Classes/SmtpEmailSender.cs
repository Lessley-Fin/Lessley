using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Services.Interfaces;
using MailKit.Net.Smtp;
using MailKit.Security;
using Microsoft.Extensions.Options;
using MimeKit;
using MimeKit.Text;

namespace Lessley.Gateway.Api.Services.Classes;

/// <summary>
/// Sends over SMTP with MailKit. Works with any submission-port provider (Gmail app password,
/// SendGrid, Mailtrap, a local MailHog) — only <c>EmailConfig</c> changes between them.
/// </summary>
public class SmtpEmailSender : IEmailSender
{
    private readonly EmailConfig _config;
    private readonly ILogger<SmtpEmailSender> _logger;

    public SmtpEmailSender(IOptions<EmailConfig> config, ILogger<SmtpEmailSender> logger)
    {
        _config = config.Value;
        _logger = logger;
    }

    public async Task SendAsync(EmailMessage message, CancellationToken ct = default)
    {
        var mime = new MimeMessage();
        mime.From.Add(new MailboxAddress(_config.FromName, _config.FromAddress));
        mime.To.Add(MailboxAddress.Parse(message.To));
        mime.Subject = message.Subject;
        mime.Body = new BodyBuilder
        {
            HtmlBody = message.HtmlBody,
            TextBody = message.TextBody,
        }.ToMessageBody();

        using var client = new SmtpClient { Timeout = _config.TimeoutSeconds * 1000 };

        // Port 465 is implicit TLS ("SMTPS"); 587 negotiates STARTTLS after connecting.
        var socketOptions = _config.Port == 465
            ? SecureSocketOptions.SslOnConnect
            : _config.UseStartTls
                ? SecureSocketOptions.StartTls
                : SecureSocketOptions.Auto;

        await client.ConnectAsync(_config.Host, _config.Port, socketOptions, ct);

        // Local relays (MailHog, Papercut) accept anonymous submission.
        if (!string.IsNullOrEmpty(_config.UserName))
            await client.AuthenticateAsync(_config.UserName, _config.Password, ct);

        await client.SendAsync(mime, ct);
        await client.DisconnectAsync(true, ct);

        // Never log the body — it carries the one-time code.
        _logger.LogInformation("Sent auth email {Subject} to {Recipient}", message.Subject, Mask(message.To));
    }

    private static string Mask(string email)
    {
        var at = email.IndexOf('@');
        if (at <= 1) return "***";
        return $"{email[0]}***{email[at..]}";
    }
}
