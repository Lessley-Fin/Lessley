using Lessley.Gateway.Api.Models;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using MongoDB.EntityFrameworkCore.Extensions;

namespace Lessley.Gateway.Api.Data
{
    public class ApplicationDbContext : IdentityDbContext<IdentityUser>
    {
        public DbSet<RefreshToken> RefreshTokens { get; set; }

        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options) : base(options) 
        {
            Database.AutoTransactionBehavior = AutoTransactionBehavior.Never;
        }

        protected override void OnModelCreating(ModelBuilder builder)
        {
            base.OnModelCreating(builder);

            // Optional but recommended: Rename the default Identity collections 
            // from things like "AspNetUsers" to cleaner MongoDB collection names.
            builder.Entity<IdentityUser>().ToCollection("users");
            builder.Entity<IdentityRole>().ToCollection("roles");
            builder.Entity<IdentityUserRole<string>>().ToCollection("user_roles");
            builder.Entity<IdentityUserClaim<string>>().ToCollection("user_claims");
            builder.Entity<IdentityUserLogin<string>>().ToCollection("user_logins");
            builder.Entity<IdentityRoleClaim<string>>().ToCollection("role_claims");
            builder.Entity<IdentityUserToken<string>>().ToCollection("user_tokens");
        }
    }
}
