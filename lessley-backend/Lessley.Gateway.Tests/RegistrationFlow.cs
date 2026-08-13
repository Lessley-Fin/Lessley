using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Xunit;

namespace Lessley.Gateway.Tests;

/// <summary>
/// Drives the staged registration the way the SPA does — start, read the emailed code, verify,
/// complete. Tests that only need "an account exists" call <see cref="RegisterAsync"/>; tests that
/// exercise the flow itself call the individual steps.
/// </summary>
internal static class RegistrationFlow
{
    /// <summary>Runs the whole handshake and returns the completion response (which sets cookies).</summary>
    public static async Task<HttpResponseMessage> RegisterAsync(
        HttpClient http,
        CapturingEmailSender emails,
        string userName,
        string email,
        string password = "Test1234!",
        object? preferences = null)
    {
        var token = await StartAsync(http, userName, email, password);
        Assert.NotNull(token);

        await VerifyAsync(http, emails, token!, email);
        return await CompleteAsync(http, token!, preferences);
    }

    /// <summary>Starts a registration and returns its token, or null if the start was rejected.</summary>
    public static async Task<string?> StartAsync(
        HttpClient http, string userName, string email, string password = "Test1234!")
    {
        var response = await http.PostAsJsonAsync("api/auth/register/start",
            new { UserName = userName, Email = email, Password = password });

        if (response.StatusCode != HttpStatusCode.OK) return null;

        var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        return body.RootElement.GetProperty("registrationToken").GetString();
    }

    public static async Task<HttpResponseMessage> VerifyAsync(
        HttpClient http, CapturingEmailSender emails, string registrationToken, string email)
    {
        var code = emails.LatestCodeFor(email);
        Assert.NotNull(code);

        return await http.PostAsJsonAsync("api/auth/register/verify-email",
            new { RegistrationToken = registrationToken, Code = code });
    }

    public static Task<HttpResponseMessage> CompleteAsync(
        HttpClient http, string registrationToken, object? preferences = null)
    {
        if (preferences is null)
            return http.PostAsJsonAsync("api/auth/register/complete", new { RegistrationToken = registrationToken });

        // Merge the caller's preferences with the token into one flat body.
        var merged = new Dictionary<string, object?> { ["registrationToken"] = registrationToken };
        foreach (var property in preferences.GetType().GetProperties())
            merged[char.ToLowerInvariant(property.Name[0]) + property.Name[1..]] = property.GetValue(preferences);

        return http.PostAsJsonAsync("api/auth/register/complete", merged);
    }
}
