namespace Lessley.Gateway.Api.Services.Interfaces;

/// <summary>
/// Outcome of an auth-flow step. Deliberately narrow: services decide what happened, controllers
/// decide the status code, and no service ever touches <c>IActionResult</c>.
/// </summary>
public abstract record AuthOperationResult
{
    public static AuthOperationResult Ok(object payload) => new Success(payload);

    /// <summary>Caller error — bad code, expired flow, password rejected by policy.</summary>
    public static AuthOperationResult Invalid(string message) => new InvalidResult(message);

    /// <summary>Too soon or too often; the caller should wait rather than retry immediately.</summary>
    public static AuthOperationResult Throttled(string message) => new ThrottledResult(message);

    /// <summary>The step earned a signed-in session; the controller writes the cookies.</summary>
    public static AuthOperationResult WithSession(AuthSession session) => new SessionIssued(session);

    public sealed record Success(object Payload)      : AuthOperationResult;
    public sealed record InvalidResult(string Message) : AuthOperationResult;
    public sealed record ThrottledResult(string Message) : AuthOperationResult;
    public sealed record SessionIssued(AuthSession Session) : AuthOperationResult;
}
