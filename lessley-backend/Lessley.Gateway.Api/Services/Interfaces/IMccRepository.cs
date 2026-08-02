using Lessley.Gateway.Api.Models.Mcc;

namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IMccRepository
{
    Task<List<MccCategoryDto>> GetCategoriesAsync(CancellationToken ct = default);
}
