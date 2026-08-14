namespace Lessley.Gateway.Api.Services.Interfaces;

/// <summary>A single outbound message. Both bodies are supplied; clients pick what they render.</summary>
public sealed record EmailMessage(string To, string Subject, string HtmlBody, string TextBody);

/// <summary>
/// Transport for transactional email. Implemented by <c>SmtpEmailSender</c> in production and
/// by <c>LoggingEmailSender</c> in Development, where the code is written to the console instead
/// so the auth flows can be exercised without SMTP credentials.
/// </summary>
public interface IEmailSender
{
    Task SendAsync(EmailMessage message, CancellationToken ct = default);
}
