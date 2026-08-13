using Lessley.Gateway.Api.Services.Interfaces;
using System.Net;

namespace Lessley.Gateway.Api.Services.Classes;

/// <summary>
/// Builds the three transactional auth emails. Kept as pure functions (no I/O, no DI) so the
/// services that own each flow just compose a message and hand it to <see cref="IEmailSender"/>.
/// </summary>
public static class AuthEmailTemplates
{
    public static EmailMessage RegistrationCode(string to, string code, int ttlMinutes) => Build(
        to,
        subject: "Confirm your Lessley email",
        heading: "Confirm your email",
        intro:   "Use this code to finish creating your Lessley account.",
        code:    code,
        ttlMinutes: ttlMinutes,
        footer:  "If you did not start a registration, you can ignore this email — no account has been created.");

    public static EmailMessage PasswordResetCode(string to, string code, int ttlMinutes) => Build(
        to,
        subject: "Reset your Lessley password",
        heading: "Reset your password",
        intro:   "Use this code to choose a new password.",
        code:    code,
        ttlMinutes: ttlMinutes,
        footer:  "If you did not request a password reset, ignore this email — your password is unchanged.");

    public static EmailMessage LoginCode(string to, string code, int ttlMinutes) => Build(
        to,
        subject: "Your Lessley sign-in code",
        heading: "Sign in to Lessley",
        intro:   "Use this code to sign in. It works once.",
        code:    code,
        ttlMinutes: ttlMinutes,
        footer:  "If you did not try to sign in, ignore this email and consider changing your password.");

    private static EmailMessage Build(
        string to, string subject, string heading, string intro,
        string code, int ttlMinutes, string footer)
    {
        var text =
            $"{heading}\n\n{intro}\n\nYour code: {code}\n\n" +
            $"It expires in {ttlMinutes} minutes.\n\n{footer}\n\n— Lessley";

        // Inline styles only and a table-free layout: every mail client mangles <style> blocks.
        var html = $"""
            <div style="font-family:Segoe UI,Helvetica,Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#1c2434">
              <h1 style="font-size:20px;margin:0 0 8px">{WebUtility.HtmlEncode(heading)}</h1>
              <p style="font-size:14px;line-height:1.6;margin:0 0 20px;color:#5b6478">{WebUtility.HtmlEncode(intro)}</p>
              <div style="font-size:32px;font-weight:700;letter-spacing:8px;text-align:center;padding:16px;background:#f4f6fa;border-radius:12px">{WebUtility.HtmlEncode(code)}</div>
              <p style="font-size:13px;line-height:1.6;margin:20px 0 0;color:#5b6478">This code expires in {ttlMinutes} minutes.</p>
              <p style="font-size:12px;line-height:1.6;margin:16px 0 0;color:#8a92a6">{WebUtility.HtmlEncode(footer)}</p>
            </div>
            """;

        return new EmailMessage(to, subject, html, text);
    }
}
