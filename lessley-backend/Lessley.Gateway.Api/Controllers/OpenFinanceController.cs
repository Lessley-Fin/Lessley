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

        // Email is the system-wide primary identifier and is exactly what Open Finance
        // expects as its userId, so it is passed straight through.
        [HttpPost("access-token/{email}")]
        public async Task<IActionResult> CreateAccessToken([FromRoute] string email)
        {
            var accessToken = await _openFinanceService.CreateAccessToken(email);
            return Ok(accessToken);
        }

        [HttpGet("connection/{email}")]
        public async Task<IActionResult> CreateNewConnection([FromRoute] string email)
        {
            var accessToken = await _openFinanceService.InitiateConnectionJourney(email);

            // TODO: In a real application, we want the client to handle the redirection to the Connect URL, but for demonstration purposes, we will redirect directly from the API.
            return Redirect(accessToken.ConnectUrl);

            //return Ok(accessToken);
        }

        [HttpGet("transactions/{email}")]
        public async Task<IActionResult> GetTransactions([FromRoute] string email)
        {
            var accessToken = await _openFinanceService.GetTransactions(email);
            return Ok(accessToken);
        }
    }
}
