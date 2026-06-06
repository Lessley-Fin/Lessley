namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IUserTagService
{
    Task AssignTagsAsync(string userId, string[] tags, CancellationToken ct = default);
}
