using Lessley.Gateway.Api.Services.Interfaces;
using System.Collections.Concurrent;
using System.Text.RegularExpressions;

namespace Lessley.Gateway.Tests;

/// <summary>
/// Test transport that keeps every message instead of sending it, so the flows can be driven the
/// way a real user drives them — read the code out of the email, then present it.
/// </summary>
public sealed class CapturingEmailSender : IEmailSender
{
    private readonly ConcurrentQueue<EmailMessage> _messages = new();

    public Task SendAsync(EmailMessage message, CancellationToken ct = default)
    {
        _messages.Enqueue(message);
        return Task.CompletedTask;
    }

    public IReadOnlyCollection<EmailMessage> Messages => _messages.ToArray();

    /// <summary>The code from the most recent message to an address, or null if none was sent.</summary>
    public string? LatestCodeFor(string email)
    {
        var message = _messages
            .Where(m => string.Equals(m.To, email, StringComparison.OrdinalIgnoreCase))
            .LastOrDefault();

        if (message is null) return null;

        var match = Regex.Match(message.TextBody, @"Your code: (\d{4,10})");
        return match.Success ? match.Groups[1].Value : null;
    }

    public int CountFor(string email) =>
        _messages.Count(m => string.Equals(m.To, email, StringComparison.OrdinalIgnoreCase));

    public void Clear()
    {
        while (_messages.TryDequeue(out _)) { }
    }
}
