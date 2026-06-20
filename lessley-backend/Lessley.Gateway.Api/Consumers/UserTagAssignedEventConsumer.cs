using Lessley.Gateway.Api.Contracts;
using Lessley.Gateway.Api.Models;
using Lessley.Gateway.Api.Services.Interfaces;
using MassTransit;
using Microsoft.AspNetCore.Identity;

namespace Lessley.Gateway.Api.Consumers;

public class UserTagAssignedEventConsumer : IConsumer<UserTagAssignedEvent>
{
    private readonly IUserTagService _userTagService;
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly ILogger<UserTagAssignedEventConsumer> _logger;

    public UserTagAssignedEventConsumer(
        IUserTagService userTagService,
        UserManager<ApplicationUser> userManager,
        ILogger<UserTagAssignedEventConsumer> logger)
    {
        _userTagService = userTagService;
        _userManager    = userManager;
        _logger         = logger;
    }

    public async Task Consume(ConsumeContext<UserTagAssignedEvent> context)
    {
        var email = context.Message.UserId;

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null)
        {
            _logger.LogWarning("UserTagAssigned: user {Email} not found — skipping", email);
            return;
        }

        await _userTagService.AssignTagsAsync(email, context.Message.Tags, context.CancellationToken);

        _logger.LogInformation(
            "UserTagAssignedEvent consumed — tags assigned to {Email}: {Tags}",
            email, string.Join(", ", context.Message.Tags));
    }
}
