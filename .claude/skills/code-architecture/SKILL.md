---
name: code-architecture
description: 'Explains and enforces the layered architecture used in Lessley services. Use when: reviewing or writing controllers, services, or repositories; deciding where new logic should live; or ensuring a controller does not contain business logic.'
argument-hint: 'code-architecture for repository/service/controller layer guidance'
user-invocable: true
---

# Code Architecture — Repository / Service / Controller

Lessley's backend follows a strict three-layer architecture. Every piece of code should belong to exactly one layer, and layers only communicate downward.

```
Controller  →  Service  →  Repository
   (HTTP)     (Logic)       (DB)
```

---

## Layer 1: Repository — Database Access Only

**What it does:** connects to the database and performs CRUD operations. Nothing else.

**Rules:**
- Contains `Save`, `GetBy*`, `Update`, `Delete` methods
- Returns domain models or raw data — never HTTP types
- No business decisions, no conditionals on business state
- No calls to other services

**Example:**
```csharp
// ✅ Correct
public class NotificationRepository : INotificationRepository
{
    public Task SaveAsync(Notification n, CancellationToken ct) => ...
    public Task<List<Notification>> GetByIdsAsync(IEnumerable<ObjectId> ids, CancellationToken ct) => ...
}

// ❌ Wrong — repository deciding business logic
public class NotificationRepository
{
    public Task SaveIfUserIsActiveAsync(Notification n) { ... } // business check = wrong layer
}
```

---

## Layer 2: Service — All Business Logic Lives Here

**What it does:** orchestrates, decides, and transforms. The service is the only layer that should contain `if` statements based on business rules.

**Rules:**
- Receives inputs from the controller (DTOs, primitives)
- Calls one or more repositories to read/write data
- Contains all validation, authorization checks, calculations, and orchestration
- Returns result types or throws domain exceptions — never `IActionResult`
- Never imports `Microsoft.AspNetCore.Mvc`

**Example:**
```csharp
// ✅ Correct
public class UserService : IUserService
{
    public async Task<UserOperationResult> UpdateAsync(string email, UpdateUserDto dto, ClaimsPrincipal caller, ...)
    {
        if (!caller.IsInRole("Admin") && caller.Email != email)
            return UserOperationResult.Forbidden();         // auth logic → service

        var user = await _userManager.FindByEmailAsync(email);
        if (user is null) return UserOperationResult.NotFound();

        var mutedChanged = ...; // business comparison → service
        ...
        if (mutedChanged)
            await _userTagService.SyncGroupsAsync(...);     // orchestration → service
    }
}

// ❌ Wrong — business logic leaking into controller
public class UserController
{
    public async Task<IActionResult> UpdateUser(string email, UpdateUserDto dto)
    {
        var user = await _userManager.FindByEmailAsync(email);
        var matchChanged = dto.MatchingScore != user.MatchingScore; // ← belongs in service
        if (matchChanged) await _personalizationService.Recalculate(...); // ← belongs in service
    }
}
```

---

## Layer 3: Controller — HTTP Plumbing Only

**What it does:** maps HTTP requests to service calls, and service results to HTTP responses.

**Rules:**
- Injects exactly ONE service per controller (the service for that resource)
- Calls one service method per action
- Maps results to `IActionResult` (`Ok`, `NotFound`, `Forbid`, `BadRequest`)
- Contains NO business logic, NO conditionals on business state
- May extract claims from `HttpContext` and pass them to the service — but does not act on them

**Example:**
```csharp
// ✅ Correct — controller is pure plumbing
public class UserController : ControllerBase
{
    private readonly IUserService _userService;

    [HttpPatch("{email}")]
    public async Task<IActionResult> UpdateUser(string email, [FromBody] UpdateUserDto dto, CancellationToken ct)
    {
        var result = await _userService.UpdateAsync(email, dto, User, ct);
        return result switch
        {
            UserOperationResult.NotFoundResult   => NotFound(),
            UserOperationResult.ForbiddenResult  => Forbid(),
            UserOperationResult.BadRequestResult e => BadRequest(e.Payload),
            UserOperationResult.Success          s => Ok(s.Payload),
            _ => throw new InvalidOperationException()
        };
    }
}
```

---

## Quick Decision Guide

| Question | Answer |
|---|---|
| "Does this touch the database?" | Repository |
| "Does this contain a business rule or decision?" | Service |
| "Does this parse HTTP input or return HTTP output?" | Controller |
| "Should controllers call repositories directly?" | **Never** |
| "Can a service return IActionResult?" | **Never** |
| "Can a repository call a service?" | **Never** |

---

## Python Equivalent (Personalization Service)

The same pattern applies in Python FastAPI:

| Layer | Python example |
|---|---|
| Repository | `UserRepository` — `get_user()`, `get_user_tags()` |
| Service | `InsightsService`, `RecommendationService` — calculation, orchestration, publishing |
| Controller (Router) | `insights_controller.py`, `recommendation_controller.py` — calls service, returns JSON |

```python
# ✅ Correct router — zero logic
@router.get("/categories")
async def calculate_user_categories(req: InsightsCalcRequests = Query()):
    service = DIContainer.get_insights_service()
    categories = await service.calculate_user_categories_async(req.email, ...)
    return PaginatedResponse(status="success", data=categories, count=len(categories))

# ❌ Wrong — logic in router
@router.get("/categories")
async def calculate_user_categories(req: InsightsCalcRequests = Query()):
    if not req.email:            # ← validation = service concern
        raise HTTPException(...)
    user = await db.find_user(req.email)   # ← db access = repository concern
    ...
```
