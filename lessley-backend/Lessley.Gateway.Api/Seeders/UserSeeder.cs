using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Models;
using Microsoft.AspNetCore.Identity;

namespace Lessley.Gateway.Api.Seeders
{
    public static class UserSeeder
    {
        public static async Task SeedAsync(IServiceProvider serviceProvider)
        {
            var userManager   = serviceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var configuration = serviceProvider.GetRequiredService<IConfiguration>();

            var username = configuration["Bootstrap:Username"] ?? "";
            var password = configuration["Bootstrap:Password"] ?? "";
            var email    = configuration["Bootstrap:Email"]    ?? "";

            if (username == "" || password == "" || email == "")
                return;

            if (await userManager.FindByNameAsync(username) is not null)
                return;

            var user   = new ApplicationUser { UserName = username, Email = email };
            var result = await userManager.CreateAsync(user, password);

            if (!result.Succeeded)
                throw new InvalidOperationException(
                    $"Bootstrap user creation failed: {string.Join(", ", result.Errors.Select(e => e.Description))}");

            result = await userManager.AddToRoleAsync(user, UserRoles.Admin.ToString());

            if (!result.Succeeded)
                throw new InvalidOperationException(
                    $"Bootstrap role assignment failed: {string.Join(", ", result.Errors.Select(e => e.Description))}");
        }
    }
}
