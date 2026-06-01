using Microsoft.AspNetCore.Identity;

namespace Lessley.Gateway.Api.Models;

public class ApplicationUser : IdentityUser
{
    public List<string>? Tags { get; set; } = new();
}
