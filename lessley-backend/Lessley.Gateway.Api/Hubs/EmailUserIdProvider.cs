using Microsoft.AspNetCore.SignalR;
using System.Security.Claims;

namespace Lessley.Gateway.Api.Hubs;

public class EmailUserIdProvider : IUserIdProvider
{
    public string? GetUserId(HubConnectionContext connection)
        => connection.User?.FindFirst(ClaimTypes.Email)?.Value;
}
