using Lessley.Gateway.Api.Enums;
using Microsoft.AspNetCore.Identity;

namespace Lessley.Gateway.Api.Seeders
{
    public static class RoleSeeder
    {
        public static async Task SeedAsync(IServiceProvider serviceProvider)
        {
            var roleManager = serviceProvider.GetRequiredService<RoleManager<IdentityRole>>();
            string[] roles = [UserRoles.Viewer.ToString(), UserRoles.Operator.ToString(), UserRoles.Admin.ToString()];

            foreach (var role in roles)
            {
                if (!await roleManager.RoleExistsAsync(role))
                {
                    await roleManager.CreateAsync(new IdentityRole(role));
                }
            }
        }
    }
}
