using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Models.Auth;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.Extensions.Options;
using System.Net.Mime;

namespace Lessley.Gateway.Api.Controllers;

/// <summary>
/// The staged registration handshake: start → verify-email → complete. No account exists until
/// the final call, so a user who walks away mid-wizard leaves nothing behind and must begin again.
/// </summary>
[Route("api/auth/register")]
[ApiController]
[Produces(MediaTypeNames.Application.Json)]
[EnableRateLimiting("auth")]
public class RegistrationController : ControllerBase
{
    private readonly IRegistrationService _registrationService;
    private readonly AuthConfig _authConfig;

    public RegistrationController(IRegistrationService registrationService, IOptions<AuthConfig> authConfig)
    {
        _registrationService = registrationService;
        _authConfig          = authConfig.Value;
    }

    /// <summary>Begins a registration and emails a verification code. Creates no user.</summary>
    [HttpPost("start")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Start([FromBody] StartRegistrationDto dto, CancellationToken ct)
        => Map(await _registrationService.StartAsync(dto, ct));

    /// <summary>Confirms the emailed code.</summary>
    [HttpPost("verify-email")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> VerifyEmail([FromBody] VerifyRegistrationDto dto, CancellationToken ct)
        => Map(await _registrationService.VerifyEmailAsync(dto, ct));

    /// <summary>Emails a replacement verification code.</summary>
    [HttpPost("resend-code")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status429TooManyRequests)]
    public async Task<IActionResult> ResendCode([FromBody] ResendRegistrationCodeDto dto, CancellationToken ct)
        => Map(await _registrationService.ResendCodeAsync(dto, ct));

    /// <summary>Creates the account and signs the user in via the usual httpOnly cookies.</summary>
    [HttpPost("complete")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Complete([FromBody] CompleteRegistrationDto dto, CancellationToken ct)
        => Map(await _registrationService.CompleteAsync(dto, ct));

    private IActionResult Map(AuthOperationResult result) =>
        AuthResultMapper.ToActionResult(this, result, _authConfig);
}
