using Lessley.Gateway.Api.Configuration;
using Lessley.Gateway.Api.Models.Auth;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.Extensions.Options;
using System.Net.Mime;

namespace Lessley.Gateway.Api.Controllers;

/// <summary>Emailed password reset: forgot → verify-code → reset.</summary>
[Route("api/auth/password")]
[ApiController]
[Produces(MediaTypeNames.Application.Json)]
[EnableRateLimiting("auth")]
public class PasswordController : ControllerBase
{
    private readonly IPasswordResetService _passwordResetService;
    private readonly AuthConfig _authConfig;

    public PasswordController(IPasswordResetService passwordResetService, IOptions<AuthConfig> authConfig)
    {
        _passwordResetService = passwordResetService;
        _authConfig           = authConfig.Value;
    }

    /// <summary>Emails a reset code. Answers the same way whether or not the address has an account.</summary>
    [HttpPost("forgot")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status429TooManyRequests)]
    public async Task<IActionResult> Forgot([FromBody] ForgotPasswordDto dto, CancellationToken ct)
        => Map(await _passwordResetService.RequestAsync(dto, ct));

    /// <summary>Exchanges a valid code for a single-use reset ticket.</summary>
    [HttpPost("verify-code")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> VerifyCode([FromBody] VerifyPasswordResetCodeDto dto, CancellationToken ct)
        => Map(await _passwordResetService.VerifyCodeAsync(dto, ct));

    /// <summary>Sets the new password. Signs the account out of every existing session.</summary>
    [HttpPost("reset")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Reset([FromBody] ResetPasswordDto dto, CancellationToken ct)
        => Map(await _passwordResetService.ResetAsync(dto, ct));

    private IActionResult Map(AuthOperationResult result) =>
        AuthResultMapper.ToActionResult(this, result, _authConfig);
}
