using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Net.Mime;
using System.Security.Claims;

namespace Lessley.Gateway.Api.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    [Authorize]
    [Produces(MediaTypeNames.Application.Json)]
    public class OpenFinanceController : ControllerBase
    {
        private readonly IOpenFinanceService _openFinanceService;

        public OpenFinanceController(
            IOpenFinanceService openFinanceService
            )
        {
            _openFinanceService = openFinanceService;
        }

        // The user's identity always comes from the authenticated JWT — never from the
        // request, so a caller can only ever act on their own Open Finance data.
        // Email is the system-wide primary identifier and is exactly what Open Finance
        // expects as its userId.

        /// <summary>Creates an Open Finance API access token for the authenticated user.</summary>
        [HttpPost("access-token")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        public async Task<IActionResult> CreateAccessToken()
        {
            var accessToken = await _openFinanceService.CreateAccessToken(CallerEmail());
            return Ok(accessToken);
        }

        /// <summary>Initiates the Open Finance bank-connection journey for the authenticated user.</summary>
        /// <remarks>Redirects the caller to the Open Finance Connect URL so the user can link their bank account.</remarks>
        [HttpGet("connection")]
        [ProducesResponseType(StatusCodes.Status302Found)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        public async Task<IActionResult> CreateNewConnection([FromQuery] string? returnUrl = null)
        {
            var accessToken = await _openFinanceService.InitiateConnectionJourney(CallerEmail(), returnUrl);

            // TODO: In a real application, we want the client to handle the redirection to the Connect URL, but for demonstration purposes, we will redirect directly from the API.
            return Redirect(accessToken.ConnectUrl);

            //return Ok(accessToken);
        }

        /// <summary>Retrieves the authenticated user's financial transactions from Open Finance.</summary>
        [HttpGet("transactions")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        public async Task<IActionResult> GetTransactions()
        {
            var accessToken = await _openFinanceService.GetTransactions(CallerEmail());
            return Ok(accessToken);
        }

        private string CallerEmail() => User.FindFirstValue(ClaimTypes.Email) ?? string.Empty;
    }
}
