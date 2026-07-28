using System.ComponentModel.DataAnnotations;

namespace Lessley.Gateway.Api.Models
{
    public class LoginDto
    {
        [Required]
        [StringLength(256, MinimumLength = 1)]
        public string UserName { get; set; } = string.Empty;

        [Required]
        [StringLength(128, MinimumLength = 1)]
        public string Password { get; set; } = string.Empty;
    }
}
