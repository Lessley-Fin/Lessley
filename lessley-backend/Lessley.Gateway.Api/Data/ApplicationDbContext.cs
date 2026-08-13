using Lessley.Gateway.Api.Models;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using MongoDB.EntityFrameworkCore.Extensions;

namespace Lessley.Gateway.Api.Data
{
    public class ApplicationDbContext : IdentityDbContext<ApplicationUser>
    {
        public DbSet<RefreshToken> RefreshTokens { get; set; }
        public DbSet<Notification> Notifications { get; set; }
        public DbSet<PendingRegistration> PendingRegistrations { get; set; }
        public DbSet<VerificationCode> VerificationCodes { get; set; }

        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options) : base(options)
        {
            Database.AutoTransactionBehavior = AutoTransactionBehavior.Never;
        }

        protected override void OnModelCreating(ModelBuilder builder)
        {
            base.OnModelCreating(builder);

            builder.Entity<ApplicationUser>().ToCollection("users");
            builder.Entity<IdentityRole>().ToCollection("roles");
            builder.Entity<IdentityUserRole<string>>().ToCollection("user_roles");
            builder.Entity<IdentityUserClaim<string>>().ToCollection("user_claims");
            builder.Entity<IdentityUserLogin<string>>().ToCollection("user_logins");
            builder.Entity<IdentityRoleClaim<string>>().ToCollection("role_claims");
            builder.Entity<IdentityUserToken<string>>().ToCollection("user_tokens");
            builder.Entity<Notification>().ToCollection("notifications");
            builder.Entity<RefreshToken>().ToCollection("refresh_tokens");
            builder.Entity<PendingRegistration>().ToCollection("pending_registrations");
            builder.Entity<VerificationCode>().ToCollection("verification_codes");
        }
    }
}
