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
    }
}
