using Lessley.Gateway.Api.Models.Club;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IClubRepository
{
    Task<List<ClubDto>> GetClubsAsync(CancellationToken ct = default);
}
