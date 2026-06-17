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
    Task<UserOperationResult> UpdateAsync(string email, UpdateUserDto dto, ClaimsPrincipal caller, CancellationToken ct = default);
    Task<UserOperationResult> RecalculateCategoriesAsync(string email, CancellationToken ct = default);
    Task<UserOperationResult> AssignTagsAsync(string email, string[] tags, CancellationToken ct = default);
}
