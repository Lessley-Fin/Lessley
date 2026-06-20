using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;

namespace Lessley.Gateway.Api.Services.Classes;

public class UserService : IUserService
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IUserTagService _userTagService;
    private readonly IPersonalizationService _personalizationService;
    private readonly ILogger<UserService> _logger;

    public UserService(
        UserManager<ApplicationUser> userManager,
        IUserTagService userTagService,
        IPersonalizationService personalizationService,
        ILogger<UserService> logger)
    {
        _userManager            = userManager;
        _userTagService         = userTagService;
        _personalizationService = personalizationService;
        _logger                 = logger;
    }

    public async Task<UserOperationResult> UpdateAsync(
        string email, UpdateUserDto dto, CancellationToken ct = default)
    {
        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return UserOperationResult.NotFound();

        var matchChanged = dto.MatchingScore.HasValue && dto.MatchingScore != user.MatchingScore;
        var mutedChanged = dto.MutedTags is not null &&
            !(user.MutedTags ?? new()).OrderBy(t => t).SequenceEqual(dto.MutedTags.OrderBy(t => t));

        if (dto.MutedTags is not null)   user.MutedTags     = dto.MutedTags;
        if (dto.Clubs is not null)       user.Clubs         = dto.Clubs;
        if (dto.MatchingScore.HasValue)  user.MatchingScore = dto.MatchingScore.Value;

        var result = await _userManager.UpdateAsync(user);
        if (!result.Succeeded)
            return UserOperationResult.BadRequest(result.Errors);

        if (mutedChanged)
            await _userTagService.SyncGroupsAsync(user.Id, user.Tags ?? new List<string>(), ct);

        if (matchChanged || mutedChanged)
        {
            try
            {
                await _personalizationService.RecalculateCategoriesAsync(email, ct);
            }
            catch (Exception ex)
            {
                // DB was saved and groups were already synced — log and continue.
                _logger.LogError(ex, "Category recalculation failed for {Email} — DB changes are saved", email);
            }
        }

        return UserOperationResult.Ok(new
        {
            email         = user.Email,
            tags          = user.Tags,
            mutedTags     = user.MutedTags,
            clubs         = user.Clubs,
            matchingScore = user.MatchingScore,
            recalculated  = matchChanged || mutedChanged,
        });
    }

    public async Task<UserOperationResult> RecalculateCategoriesAsync(string email, CancellationToken ct = default)
    {
        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return UserOperationResult.NotFound();

        await _personalizationService.RecalculateCategoriesAsync(email, ct);
        return UserOperationResult.Ok(new { });
    }

    public async Task<UserOperationResult> AssignTagsAsync(string email, string[] tags, CancellationToken ct = default)
    {
        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return UserOperationResult.NotFound();

        await _userTagService.AssignTagsAsync(user.Id, tags, ct);
        return UserOperationResult.Ok(new { email = user.Email, tags });
    }

    public async Task<UserOperationResult> GetCategoriesAsync(string email, CancellationToken ct = default)
    {
        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return UserOperationResult.NotFound();

        return UserOperationResult.Ok(new
        {
            email      = user.Email,
            categories = user.Tags ?? new List<string>(),
        });
    }

    public async Task<List<string>?> GetUserTagsAsync(string email, CancellationToken ct = default)
    {
        var user = await _userManager.FindByEmailAsync(email);
        return user?.Tags;
    }
}
