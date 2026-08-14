using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Models.Auth;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.Extensions.Options;
using System.Net.Mime;

namespace Lessley.Gateway.Api.Controllers;

/// <summary>
/// Passwordless sign-in by emailed code. An alternative to <c>POST /api/auth/login</c>, not a
/// replacement — a verified code yields exactly the same session cookies.
/// </summary>
[Route("api/auth/login/otp")]
[ApiController]
[Produces(MediaTypeNames.Application.Json)]
[EnableRateLimiting("auth")]
public class LoginOtpController : ControllerBase
{
    private readonly ILoginOtpService _loginOtpService;
    private readonly AuthConfig _authConfig;

    public LoginOtpController(ILoginOtpService loginOtpService, IOptions<AuthConfig> authConfig)
    {
        _loginOtpService = loginOtpService;
        _authConfig      = authConfig.Value;
    }

    /// <summary>Emails a sign-in code. Answers the same way whether or not the address has an account.</summary>
    [HttpPost("request")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status429TooManyRequests)]
    // Named RequestCode, not Request — the latter hides ControllerBase.Request.
    public async Task<IActionResult> RequestCode([FromBody] RequestLoginCodeDto dto, CancellationToken ct)
        => Map(await _loginOtpService.RequestAsync(dto, ct));

    /// <summary>Redeems the code and issues the httpOnly session cookies.</summary>
    [HttpPost("verify")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Verify([FromBody] VerifyLoginCodeDto dto, CancellationToken ct)
        => Map(await _loginOtpService.VerifyAsync(dto, ct));

    private IActionResult Map(AuthOperationResult result) =>
        AuthResultMapper.ToActionResult(this, result, _authConfig);
}
