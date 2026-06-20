namespace Lessley.Gateway.Api.Services.Interfaces;

public interface IUserTagService
{
    Task AssignTagsAsync(string email, string[] tags, CancellationToken ct = default);

    Task SyncGroupsAsync(string email, IReadOnlyList<string> previousTags, CancellationToken ct = default);
}
