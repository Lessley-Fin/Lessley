using Lessley.Gateway.Api.Data;
using Lessley.Gateway.Api.Enums;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;

namespace Lessley.Gateway.Api.Services.Classes;

public class UserService : IUserService
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IUserTagService _userTagService;
    private readonly ApplicationDbContext _db;

    public UserService(
        UserManager<ApplicationUser> userManager,
        IUserTagService userTagService,
        ApplicationDbContext db)
    {
        _userManager    = userManager;
        _userTagService = userTagService;
        _db             = db;
    }

    public async Task<UserOperationResult> UpdateAsync(
        string email, UpdateUserDto dto, CancellationToken ct = default)
    {
        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return UserOperationResult.NotFound();

        double? newScore = dto.MatchLevel is not null && Enum.TryParse<MatchLevel>(dto.MatchLevel, true, out var parsed)
            ? parsed.ToMatchingScore()
            : null;

        var matchChanged = newScore.HasValue && newScore != user.MatchingScore;
        var mutedChanged = dto.MutedTags is not null &&
            !(user.MutedTags ?? new()).OrderBy(t => t).SequenceEqual(dto.MutedTags.OrderBy(t => t));

        if (dto.MutedTags is not null)  user.MutedTags     = dto.MutedTags;
        if (dto.Clubs is not null)      user.Clubs         = dto.Clubs;
        if (newScore.HasValue)          user.MatchingScore = newScore.Value;

        var result = await _userManager.UpdateAsync(user);
        if (!result.Succeeded)
            return UserOperationResult.BadRequest(result.Errors);

        if (mutedChanged)
            await _userTagService.SyncGroupsAsync(email, user.Tags ?? new List<string>(), ct);

        // Categories are no longer recalculated eagerly here — the Gateway does not call
        // Personalization over HTTP. They are recomputed on the next
        // GET /api/v1/insights/categories, which the client issues through the edge.
        return UserOperationResult.Ok(new
        {
            email      = user.Email,
            userName   = user.UserName,
            tags       = user.Tags     ?? new List<string>(),
            mutedTags  = user.MutedTags ?? new List<string>(),
            clubs      = user.Clubs    ?? new List<string>(),
            matchLevel = user.MatchingScore.ToMatchLevel(),
            // True when the change invalidates cached categories, so the client knows to
            // re-fetch insights. It no longer means "recalculation already happened".
            staleInsights = matchChanged || mutedChanged,
        });
    }

    public async Task<UserOperationResult> AssignTagsAsync(string email, string[] tags, CancellationToken ct = default)
    {
        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
            return UserOperationResult.NotFound();

        await _userTagService.AssignTagsAsync(email, tags, ct);
        return UserOperationResult.Ok(new { email = user.Email, tags });
    }

    public async Task<List<string>?> GetUserTagsAsync(string email, CancellationToken ct = default)
    {
        var user = await _userManager.FindByEmailAsync(email);
        return user?.Tags;
    }

    public async Task<UserOperationResult> GetMyConfigAsync(string email, CancellationToken ct = default)
    {
        var user = await _userManager.FindByEmailAsync(email);
        if (user is null) return UserOperationResult.NotFound();

        var userRoleIds = await _db.UserRoles
            .Where(ur => ur.UserId == user.Id)
            .Select(ur => ur.RoleId)
            .ToListAsync(ct);

        var roles = await _db.Roles
            .Where(r => userRoleIds.Contains(r.Id) && r.Name != null)
            .Select(r => r.Name!)
            .ToListAsync(ct);

        return UserOperationResult.Ok(new
        {
            email      = user.Email,
            userName   = user.UserName,
            roles,
            clubs      = user.Clubs    ?? new List<string>(),
            tags       = user.Tags     ?? new List<string>(),
            mutedTags  = user.MutedTags ?? new List<string>(),
            matchLevel = user.MatchingScore.ToMatchLevel(),
        });
    }
}
