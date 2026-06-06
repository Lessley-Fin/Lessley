using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;

namespace Lessley.Gateway.Api.Consumers;

public class UserTagAssignedEventConsumer : IConsumer<UserTagAssignedEvent>
{
    private readonly IUserTagService _userTagService;
    private readonly ILogger<UserTagAssignedEventConsumer> _logger;

    public UserTagAssignedEventConsumer(
        IUserTagService userTagService,
        ILogger<UserTagAssignedEventConsumer> logger)
    {
        _userTagService = userTagService;
        _logger         = logger;
    }

    public async Task Consume(ConsumeContext<UserTagAssignedEvent> context)
    {
        var (userId, tags) = (context.Message.UserId, context.Message.Tags);

        await _userTagService.AssignTagsAsync(userId, tags, context.CancellationToken);

        _logger.LogInformation(
            "UserTagAssignedEvent consumed — tags assigned to user {UserId}: {Tags}",
            userId, string.Join(", ", tags));
    }
}
