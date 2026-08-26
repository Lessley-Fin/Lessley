using Lessley.Gateway.Api.Models;
using Microsoft.AspNetCore.Identity;
using System.Security.Claims;

namespace Lessley.Gateway.Api.Services.Interfaces;

public abstract record UserOperationResult
{
    public static UserOperationResult Ok(object payload)   => new Success(payload);
    public static UserOperationResult NotFound()           => new NotFoundResult();
    public static UserOperationResult Forbidden()          => new ForbiddenResult();
    public static UserOperationResult BadRequest(object p) => new BadRequestResult(p);

    public sealed record Success(object Payload)           : UserOperationResult;
    public sealed record NotFoundResult                    : UserOperationResult;
    public sealed record ForbiddenResult                   : UserOperationResult;
    public sealed record BadRequestResult(object Payload)  : UserOperationResult;
}

public interface IUserService
{
    Task<UserOperationResult> UpdateAsync(string email, UpdateUserDto dto, CancellationToken ct = default);
    Task<UserOperationResult> AssignTagsAsync(string email, string[] tags, CancellationToken ct = default);
    /// <summary>Returns the user's tags from the DB, or null if the user does not exist.</summary>
    Task<List<string>?> GetUserTagsAsync(string email, CancellationToken ct = default);
    /// <summary>Returns the user's selected loyalty clubs, or null if the user does not exist.</summary>
    Task<List<string>?> GetUserClubsAsync(string email, CancellationToken ct = default);
    Task<UserOperationResult> GetMyConfigAsync(string email, CancellationToken ct = default);
}
