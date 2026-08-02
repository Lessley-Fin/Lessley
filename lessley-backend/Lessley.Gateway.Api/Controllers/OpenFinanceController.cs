using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Mvc;
using System.Net.Mime;

namespace Lessley.Gateway.Api.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
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

        // Email is the system-wide primary identifier and is exactly what Open Finance
        // expects as its userId, so it is passed straight through.

        /// <summary>Creates an Open Finance API access token for the given user.</summary>
        /// <param name="email">The user's email address (used as the Open Finance user ID).</param>
        [HttpPost("access-token/{email}")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        public async Task<IActionResult> CreateAccessToken([FromRoute] string email)
        {
            var accessToken = await _openFinanceService.CreateAccessToken(email);
            return Ok(accessToken);
        }

        /// <summary>Initiates the Open Finance bank-connection journey for a user.</summary>
        /// <remarks>Redirects the caller to the Open Finance Connect URL so the user can link their bank account.</remarks>
        /// <param name="email">The user's email address.</param>
        [HttpGet("connection/{email}")]
        [ProducesResponseType(StatusCodes.Status302Found)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        public async Task<IActionResult> CreateNewConnection([FromRoute] string email, [FromQuery] string? returnUrl = null)
        {
            var accessToken = await _openFinanceService.InitiateConnectionJourney(email, returnUrl);

            // TODO: In a real application, we want the client to handle the redirection to the Connect URL, but for demonstration purposes, we will redirect directly from the API.
            return Redirect(accessToken.ConnectUrl);

            //return Ok(accessToken);
        }

        /// <summary>Retrieves the user's financial transactions from Open Finance.</summary>
        /// <param name="email">The user's email address.</param>
        [HttpGet("transactions/{email}")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        public async Task<IActionResult> GetTransactions([FromRoute] string email)
        {
            var accessToken = await _openFinanceService.GetTransactions(email);
            return Ok(accessToken);
        }
    }
}
