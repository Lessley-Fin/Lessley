using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Mvc;

namespace Lessley.Gateway.Api.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class OpenFinanceController : ControllerBase
    {
        private readonly IOpenFinanceService _openFinanceService;

        public OpenFinanceController(
            IOpenFinanceService openFinanceService
            )
        {
            _openFinanceService = openFinanceService;
        }

        [HttpPost("access-token/{userId}")]
        public async Task<IActionResult> CreateAccessToken([FromRoute] string userId)
        {
            var accessToken = await _openFinanceService.CreateAccessToken(userId);
            return Ok(accessToken);
        }

        [HttpGet("connection/{userId}/{expiryDate}")]
        public async Task<IActionResult> CreateNewConnection([FromRoute] string userId, [FromRoute] string expiryDate)
        {
            var accessToken = await _openFinanceService.InitiateConnectionJourney(userId, expiryDate);

            // TODO: In a real application, we want the client to handle the redirection to the Connect URL, but for demonstration purposes, we will redirect directly from the API.
            return Redirect(accessToken.ConnectUrl);

            //return Ok(accessToken);
        }

        [HttpGet("transactions/{userId}")]
        public async Task<IActionResult> GetTransactions([FromRoute] string userId)
        {
            var accessToken = await _openFinanceService.GetTransactions(userId);
            return Ok(accessToken);
        }
    }
}
