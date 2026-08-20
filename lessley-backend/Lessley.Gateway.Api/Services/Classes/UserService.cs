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
    private readonly IPersonalizationService _personalizationService;
    private readonly ISendNotificationService _sendNotificationService;
    private readonly ApplicationDbContext _db;

    public UserService(
        UserManager<ApplicationUser> userManager,
        IUserTagService userTagService,
        IPersonalizationService personalizationService,
        ISendNotificationService sendNotificationService,
        ApplicationDbContext db)
    {
        _userManager             = userManager;
        _userTagService          = userTagService;
        _personalizationService  = personalizationService;
        _sendNotificationService = sendNotificationService;
        _db                      = db;
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

        // Only the match level feeds the calculation — it decides how many categories survive
        // the trim. Muted tags are applied at fanout and display time, and clubs only affect
        // missed-savings, so neither changes a single computed category; recalculating on those
        // would spend an Open Finance round trip to arrive at the same answer.
        if (matchChanged)
            await _personalizationService.TriggerCalculateUserCategoriesAsync(email, ct: ct);

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

        // AssignTagsAsync throws when the write is rejected so the bus consumer can retry it.
        // On this path there is no retry to earn — an admin is waiting — so the failure is
        // turned back into a result. Reporting success on a write that did not happen is the
        // one outcome worth ruling out.
        try
        {
            await _userTagService.AssignTagsAsync(email, tags, ct);
        }
        catch (InvalidOperationException ex)
        {
            return UserOperationResult.BadRequest(new { error = ex.Message });
        }

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
            pendingWelcomeNotification = user.WelcomeNotificationSent != true,
        });
    }

    public async Task<UserOperationResult> SendWelcomeNotificationAsync(string email, CancellationToken ct = default)
    {
        var user = await _userManager.FindByEmailAsync(email);
        if (user is null) return UserOperationResult.NotFound();

        if (user.WelcomeNotificationSent == true)
            return UserOperationResult.Ok(new { sent = false });

        await _sendNotificationService.SendToUserAsync(user.Email!, user.UserName ?? "", dealId: null, type: "welcome", ct: ct);

        user.WelcomeNotificationSent = true;
        var result = await _userManager.UpdateAsync(user);
        if (!result.Succeeded)
            return UserOperationResult.BadRequest(result.Errors);

        return UserOperationResult.Ok(new { sent = true });
    }
}
