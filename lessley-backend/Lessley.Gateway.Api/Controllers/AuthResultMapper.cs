using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Mvc;

namespace Lessley.Gateway.Api.Controllers;

/// <summary>
/// Turns an <see cref="AuthOperationResult"/> into an HTTP response. Shared by the three auth-flow
/// controllers so a session issued by registration, password login or an emailed code is
/// indistinguishable to the client.
/// </summary>
internal static class AuthResultMapper
{
    public static IActionResult ToActionResult(
        ControllerBase controller, AuthOperationResult result, AuthConfig authConfig) => result switch
    {
        AuthOperationResult.Success s => controller.Ok(s.Payload),

        AuthOperationResult.InvalidResult i =>
            controller.BadRequest(new { detail = i.Message }),

        AuthOperationResult.ThrottledResult t =>
            controller.StatusCode(StatusCodes.Status429TooManyRequests, new { detail = t.Message }),

        AuthOperationResult.SessionIssued session => IssueSession(controller, session, authConfig),

        _ => throw new InvalidOperationException($"Unhandled auth result: {result.GetType().Name}"),
    };

    private static IActionResult IssueSession(
        ControllerBase controller, AuthOperationResult.SessionIssued issued, AuthConfig authConfig)
    {
        AuthCookieWriter.SetAuthCookies(
            controller.Request, controller.Response, authConfig,
            issued.Session.AccessToken, issued.Session.RawRefreshToken);

        // Tokens live only in the cookies; the body carries nothing sensitive. Shape matches
        // AuthController.Login so the SPA has one response type for every sign-in path.
        var profile = issued.Session.Profile;
        return controller.Ok(new
        {
            userName = profile.UserName,
            email    = profile.Email,
            userId   = profile.UserId,
            roles    = profile.Roles,
        });
    }
}
