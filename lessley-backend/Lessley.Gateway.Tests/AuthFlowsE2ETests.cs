using Lessley.Gateway.Api.Models;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.DependencyInjection;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Xunit;

namespace Lessley.Gateway.Tests;

/// <summary>
/// The three production-grade auth flows: email-verified registration, forgotten password, and
/// passwordless sign-in. These run on the in-memory EF store, so no MongoDB is required.
/// </summary>
public class AuthFlowsE2ETests : IClassFixture<GatewayWebApplicationFactory>
{
    private readonly GatewayWebApplicationFactory _factory;

    public AuthFlowsE2ETests(GatewayWebApplicationFactory factory) => _factory = factory;

    // ── Registration: nothing exists until every step is done ─────────────────

    [Fact]
    public async Task Start_DoesNotCreateAUser()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("start-only");

        var token = await RegistrationFlow.StartAsync(http, userName, email);

        Assert.NotNull(token);
        Assert.Null(await FindUserAsync(email));
    }

    [Fact]
    public async Task VerifiedButNotCompleted_StillCreatesNoUser()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("verified-only");

        var token = await RegistrationFlow.StartAsync(http, userName, email);
        var verify = await RegistrationFlow.VerifyAsync(http, _factory.Emails, token!, email);

        Assert.Equal(HttpStatusCode.OK, verify.StatusCode);
        // Abandoning here is the case task 3 is about: the mailbox is proven, but walking away
        // must still leave no account behind.
        Assert.Null(await FindUserAsync(email));
    }

    [Fact]
    public async Task Complete_WithoutVerifyingEmail_IsRejectedAndCreatesNoUser()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("unverified");

        var token    = await RegistrationFlow.StartAsync(http, userName, email);
        var complete = await RegistrationFlow.CompleteAsync(http, token!);

        Assert.Equal(HttpStatusCode.BadRequest, complete.StatusCode);
        Assert.Null(await FindUserAsync(email));
    }

    [Fact]
    public async Task FullFlow_CreatesVerifiedUserAndSignsThemIn()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("full");

        var response = await RegistrationFlow.RegisterAsync(http, _factory.Emails, userName, email);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        // Completion signs the user in directly, exactly like a password login.
        var cookies = SetCookies(response);
        Assert.Contains(cookies, c => c.StartsWith("access_token="));
        Assert.Contains(cookies, c => c.StartsWith("refresh_token="));

        var user = await FindUserAsync(email);
        Assert.NotNull(user);
        Assert.True(user!.EmailConfirmed);
    }

    [Fact]
    public async Task VerifyEmail_WithWrongCode_IsRejected()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("wrong-code");

        var token = await RegistrationFlow.StartAsync(http, userName, email);

        var response = await http.PostAsJsonAsync("api/auth/register/verify-email",
            new { RegistrationToken = token, Code = "000000" });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task VerifyEmail_AfterTooManyWrongCodes_DiscardsTheRegistration()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("burned");

        var token = await RegistrationFlow.StartAsync(http, userName, email);

        // MaxAttempts defaults to 5; the fifth wrong guess destroys the pending registration.
        for (var i = 0; i < 5; i++)
        {
            await http.PostAsJsonAsync("api/auth/register/verify-email",
                new { RegistrationToken = token, Code = "000000" });
        }

        // Even the correct code is now useless — the flow must be restarted from step one.
        var withRealCode = await RegistrationFlow.VerifyAsync(http, _factory.Emails, token!, email);
        Assert.Equal(HttpStatusCode.BadRequest, withRealCode.StatusCode);
        Assert.Null(await FindUserAsync(email));
    }

    [Fact]
    public async Task Start_WithAnExistingEmail_IsRejected()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("dupe");

        await RegistrationFlow.RegisterAsync(http, _factory.Emails, userName, email);

        var second = await RegistrationFlow.StartAsync(http, $"{userName}-other", email);
        Assert.Null(second);
    }

    [Fact]
    public async Task Start_ReplacesAnEarlierUnfinishedAttempt()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("restart");

        var first = await RegistrationFlow.StartAsync(http, userName, email);
        var second = await RegistrationFlow.StartAsync(http, userName, email);

        Assert.NotNull(second);
        Assert.NotEqual(first, second);

        // The abandoned attempt's token no longer refers to anything.
        var staleVerify = await http.PostAsJsonAsync("api/auth/register/verify-email",
            new { RegistrationToken = first, Code = _factory.Emails.LatestCodeFor(email) });
        Assert.Equal(HttpStatusCode.BadRequest, staleVerify.StatusCode);
    }

    // ── Password reset ────────────────────────────────────────────────────────

    [Fact]
    public async Task ForgotPassword_ForUnknownEmail_LooksIdenticalToAKnownOne()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("enum");
        await RegistrationFlow.RegisterAsync(http, _factory.Emails, userName, email);

        var known   = await http.PostAsJsonAsync("api/auth/password/forgot", new { Email = email });
        var unknown = await http.PostAsJsonAsync("api/auth/password/forgot",
            new { Email = $"nobody-{Guid.NewGuid():N}@test.com" });

        Assert.Equal(HttpStatusCode.OK, known.StatusCode);
        Assert.Equal(HttpStatusCode.OK, unknown.StatusCode);
        Assert.Equal(
            await known.Content.ReadAsStringAsync(),
            await unknown.Content.ReadAsStringAsync());
    }

    [Fact]
    public async Task PasswordReset_FullFlow_ChangesThePasswordAndRevokesSessions()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("reset");
        await RegistrationFlow.RegisterAsync(http, _factory.Emails, userName, email);

        var ticket = await ResetToTicketAsync(http, email);

        var reset = await http.PostAsJsonAsync("api/auth/password/reset",
            new { Email = email, ResetTicket = ticket, NewPassword = "BrandNew5678!" });
        Assert.Equal(HttpStatusCode.OK, reset.StatusCode);

        // New password works, old one does not.
        using var fresh = _factory.CreateClient();
        var withNew = await fresh.PostAsJsonAsync("api/auth/login",
            new { UserName = userName, Password = "BrandNew5678!" });
        Assert.Equal(HttpStatusCode.OK, withNew.StatusCode);

        var withOld = await fresh.PostAsJsonAsync("api/auth/login",
            new { UserName = userName, Password = "Test1234!" });
        Assert.Equal(HttpStatusCode.Unauthorized, withOld.StatusCode);
    }

    [Fact]
    public async Task PasswordReset_TicketIsSingleUse()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("single-use");
        await RegistrationFlow.RegisterAsync(http, _factory.Emails, userName, email);

        var ticket = await ResetToTicketAsync(http, email);

        var first = await http.PostAsJsonAsync("api/auth/password/reset",
            new { Email = email, ResetTicket = ticket, NewPassword = "FirstNew5678!" });
        Assert.Equal(HttpStatusCode.OK, first.StatusCode);

        var replay = await http.PostAsJsonAsync("api/auth/password/reset",
            new { Email = email, ResetTicket = ticket, NewPassword = "SecondNew5678!" });
        Assert.Equal(HttpStatusCode.BadRequest, replay.StatusCode);
    }

    [Fact]
    public async Task PasswordReset_WithWrongCode_YieldsNoTicket()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("bad-reset-code");
        await RegistrationFlow.RegisterAsync(http, _factory.Emails, userName, email);

        await http.PostAsJsonAsync("api/auth/password/forgot", new { Email = email });

        var verify = await http.PostAsJsonAsync("api/auth/password/verify-code",
            new { Email = email, Code = "000000" });

        Assert.Equal(HttpStatusCode.BadRequest, verify.StatusCode);
    }

    // ── Passwordless login ────────────────────────────────────────────────────

    [Fact]
    public async Task LoginOtp_FullFlow_SignsTheUserIn()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("otp");
        await RegistrationFlow.RegisterAsync(http, _factory.Emails, userName, email);

        using var fresh = _factory.CreateClient();
        var requested = await fresh.PostAsJsonAsync("api/auth/login/otp/request", new { Email = email });
        Assert.Equal(HttpStatusCode.OK, requested.StatusCode);

        var code = _factory.Emails.LatestCodeFor(email);
        Assert.NotNull(code);

        var verified = await fresh.PostAsJsonAsync("api/auth/login/otp/verify",
            new { Email = email, Code = code });

        Assert.Equal(HttpStatusCode.OK, verified.StatusCode);
        var cookies = SetCookies(verified);
        Assert.Contains(cookies, c => c.StartsWith("access_token="));
        Assert.Contains(cookies, c => c.StartsWith("refresh_token="));

        // The session is real: an authenticated endpoint now answers.
        var me = await fresh.GetAsync("api/user/me");
        Assert.Equal(HttpStatusCode.OK, me.StatusCode);
    }

    [Fact]
    public async Task LoginOtp_CodeIsSingleUse()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("otp-replay");
        await RegistrationFlow.RegisterAsync(http, _factory.Emails, userName, email);

        using var fresh = _factory.CreateClient();
        await fresh.PostAsJsonAsync("api/auth/login/otp/request", new { Email = email });
        var code = _factory.Emails.LatestCodeFor(email);

        var first = await fresh.PostAsJsonAsync("api/auth/login/otp/verify", new { Email = email, Code = code });
        Assert.Equal(HttpStatusCode.OK, first.StatusCode);

        var replay = await fresh.PostAsJsonAsync("api/auth/login/otp/verify", new { Email = email, Code = code });
        Assert.Equal(HttpStatusCode.BadRequest, replay.StatusCode);
    }

    [Fact]
    public async Task LoginOtp_RequestForUnknownEmail_LooksIdenticalAndSendsNothing()
    {
        using var http = _factory.CreateClient();
        var unknown = $"nobody-{Guid.NewGuid():N}@test.com";

        var response = await http.PostAsJsonAsync("api/auth/login/otp/request", new { Email = unknown });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(0, _factory.Emails.CountFor(unknown));
    }

    [Fact]
    public async Task LoginOtp_WithWrongCode_IsRejected()
    {
        using var http = _factory.CreateClient();
        var (userName, email) = Identity("otp-wrong");
        await RegistrationFlow.RegisterAsync(http, _factory.Emails, userName, email);

        await http.PostAsJsonAsync("api/auth/login/otp/request", new { Email = email });

        var verified = await http.PostAsJsonAsync("api/auth/login/otp/verify",
            new { Email = email, Code = "000000" });

        Assert.Equal(HttpStatusCode.BadRequest, verified.StatusCode);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static (string UserName, string Email) Identity(string prefix)
    {
        var userName = $"{prefix}-{Guid.NewGuid():N}";
        return (userName, $"{userName}@test.com");
    }

    private async Task<ApplicationUser?> FindUserAsync(string email)
    {
        using var scope = _factory.Services.CreateScope();
        var userManager = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        return await userManager.FindByEmailAsync(email);
    }

    /// <summary>Runs forgot → verify-code and returns the reset ticket.</summary>
    private async Task<string> ResetToTicketAsync(HttpClient http, string email)
    {
        var requested = await http.PostAsJsonAsync("api/auth/password/forgot", new { Email = email });
        Assert.Equal(HttpStatusCode.OK, requested.StatusCode);

        var code = _factory.Emails.LatestCodeFor(email);
        Assert.NotNull(code);

        var verify = await http.PostAsJsonAsync("api/auth/password/verify-code",
            new { Email = email, Code = code });
        Assert.Equal(HttpStatusCode.OK, verify.StatusCode);

        var body = JsonDocument.Parse(await verify.Content.ReadAsStringAsync());
        return body.RootElement.GetProperty("resetTicket").GetString()!;
    }

    private static List<string> SetCookies(HttpResponseMessage response) =>
        response.Headers.TryGetValues("Set-Cookie", out var values) ? values.ToList() : new List<string>();
}
