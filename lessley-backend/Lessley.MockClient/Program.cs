using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.SignalR.Client;

// ── Setup ────────────────────────────────────────────────────────────────────

Console.Title = "Lessley Mock Client";

var baseUrl = args.Length > 0 ? args[0].TrimEnd('/') : "http://localhost:5001";

Banner($"Lessley Mock Client  |  {baseUrl}");

// ── Authenticate ─────────────────────────────────────────────────────────────

Console.Write("Username : ");
var username = Console.ReadLine() ?? string.Empty;
Console.Write("Password : ");
var password = ReadPassword();
Console.WriteLine();

var token = await LoginAsync(baseUrl, username, password);
if (token is null)
{
    Error("Login failed — check credentials and that the Gateway is running.");
    return;
}

var myUserId = ExtractUserIdFromJwt(token) ?? "unknown";
Ok($"Authenticated as '{username}'  (userId: {myUserId})");

// ── Build SignalR connection ───────────────────────────────────────────────────

var hub = new HubConnectionBuilder()
    .WithUrl($"{baseUrl}/hubs/notifications", options =>
    {
        options.AccessTokenProvider = () => Task.FromResult<string?>(token);
    })
    .WithAutomaticReconnect()
    .Build();

// Receive notifications from server
hub.On<JsonElement>("DealUserNotification",  OnNotificationReceived);
hub.On<JsonElement>("DealGroupNotification", OnNotificationReceived);

hub.Closed += ex =>
{
    Warn($"Disconnected — {ex?.Message ?? "connection closed"}");
    return Task.CompletedTask;
};

hub.Reconnected += connectionId =>
{
    Ok($"Reconnected  (connection: {connectionId})");
    return Task.CompletedTask;
};

hub.Reconnecting += ex =>
{
    Warn($"Reconnecting… ({ex?.Message})");
    return Task.CompletedTask;
};

// Graceful Ctrl+C shutdown
using var cts = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) => { e.Cancel = true; cts.Cancel(); };

try
{
    await hub.StartAsync(cts.Token);
}
catch (Exception ex)
{
    Error($"Could not connect to hub: {ex.Message}");
    return;
}

Ok($"Connected to hub  (connection: {hub.ConnectionId})");
Console.WriteLine($"  Your userId : {myUserId}  ← use this in 'send user' from the other client");
PrintHelp();

// ── Interactive loop ──────────────────────────────────────────────────────────

using var http = new HttpClient { BaseAddress = new Uri(baseUrl) };
http.DefaultRequestHeaders.Authorization = new("Bearer", token);

while (!cts.Token.IsCancellationRequested)
{
    Console.Write("> ");
    string input;
    try { input = (Console.ReadLine() ?? "").Trim(); }
    catch (OperationCanceledException) { break; }

    if (string.IsNullOrWhiteSpace(input)) continue;

    if (input is "q" or "quit" or "exit") break;

    if (input is "?" or "help") { PrintHelp(); continue; }

    if (input is "whoami")
    {
        Console.WriteLine($"  username : {username}");
        Console.WriteLine($"  userId   : {myUserId}");
        continue;
    }

    if (input.StartsWith("send user ", StringComparison.OrdinalIgnoreCase))
    {
        var rest = input["send user ".Length..].Split(' ', 2, StringSplitOptions.RemoveEmptyEntries);
        if (rest.Length < 2) { Warn("Usage: send user <userId> <message>"); continue; }
        await SendToUserAsync(http, rest[0], rest[1]);
        continue;
    }

    if (input.StartsWith("send group ", StringComparison.OrdinalIgnoreCase))
    {
        var rest = input["send group ".Length..].Split(' ', 2, StringSplitOptions.RemoveEmptyEntries);
        if (rest.Length < 2) { Warn("Usage: send group <tag> <message>"); continue; }
        await SendToGroupAsync(http, rest[0], rest[1]);
        continue;
    }

    if (input.StartsWith("status ", StringComparison.OrdinalIgnoreCase))
    {
        var userId = input["status ".Length..].Trim();
        await GetStatusAsync(http, userId);
        continue;
    }

    Warn("Unknown command — type 'help' for options.");
}

await hub.StopAsync();
Console.WriteLine("\nGoodbye.");

// ── Handlers ─────────────────────────────────────────────────────────────────

static void OnNotificationReceived(JsonElement payload)
{
    var msg       = payload.TryGetProperty("message",   out var m)  ? m.GetString()  : null;
    var type      = payload.TryGetProperty("type",      out var t)  ? t.GetString()  : null;
    var group     = payload.TryGetProperty("group",     out var g)  ? g.GetString()  : null;
    var timestamp = payload.TryGetProperty("timestamp", out var ts) ? ts.GetString() : DateTime.UtcNow.ToString("O");

    Console.WriteLine();
    Console.ForegroundColor = ConsoleColor.Cyan;
    Console.WriteLine($"[NOTIFICATION] {timestamp}");
    Console.ResetColor();
    Console.WriteLine($"  type    : {type}");
    if (group is not null) Console.WriteLine($"  group   : {group}");
    Console.WriteLine($"  message : {msg}");
    Console.Write("> ");
}

// ── API helpers ───────────────────────────────────────────────────────────────

static async Task<string?> LoginAsync(string baseUrl, string username, string password)
{
    using var http = new HttpClient { BaseAddress = new Uri(baseUrl) };
    try
    {
        var response = await http.PostAsJsonAsync("api/auth/login", new { userName = username, password });
        if (!response.IsSuccessStatusCode) return null;

        var doc = await response.Content.ReadFromJsonAsync<JsonDocument>();
        return doc?.RootElement.GetProperty("accessToken").GetString();
    }
    catch
    {
        return null;
    }
}

static async Task SendToUserAsync(HttpClient http, string userId, string message)
{
    try
    {
        var response = await http.PostAsJsonAsync($"api/notification/user/{userId}", new { message });
        var body = await response.Content.ReadAsStringAsync();
        if (response.IsSuccessStatusCode) Ok(body);
        else Error($"{(int)response.StatusCode} — {body}");
    }
    catch (Exception ex) { Error(ex.Message); }
}

static async Task SendToGroupAsync(HttpClient http, string tag, string message)
{
    try
    {
        var response = await http.PostAsJsonAsync($"api/notification/group/{tag}", new { message });
        var body = await response.Content.ReadAsStringAsync();
        if (response.IsSuccessStatusCode) Ok(body);
        else Error($"{(int)response.StatusCode} — {body}");
    }
    catch (Exception ex) { Error(ex.Message); }
}

static async Task GetStatusAsync(HttpClient http, string userId)
{
    try
    {
        var response = await http.GetAsync($"api/notification/status/{userId}");
        var body     = await response.Content.ReadAsStringAsync();
        if (response.IsSuccessStatusCode) Ok(body);
        else Error($"{(int)response.StatusCode} — {body}");
    }
    catch (Exception ex) { Error(ex.Message); }
}

// ── Console helpers ───────────────────────────────────────────────────────────

static void PrintHelp()
{
    Console.WriteLine();
    Console.WriteLine("  whoami                         — show your userId (needed by the other client)");
    Console.WriteLine("  send user <userId> <message>   — send a notification to a user  (requires Admin role)");
    Console.WriteLine("  send group <tag> <message>     — broadcast to a group            (requires Admin role)");
    Console.WriteLine("  status <userId>                — check whether a user is connected");
    Console.WriteLine("  help / ?                       — show this help");
    Console.WriteLine("  quit / q  or  Ctrl+C           — exit");
    Console.WriteLine();
}

// Decodes the JWT payload (no library needed — it's just base64url JSON)
static string? ExtractUserIdFromJwt(string token)
{
    try
    {
        var payload = token.Split('.')[1];
        // base64url → base64
        payload = payload.Replace('-', '+').Replace('_', '/');
        payload = payload.PadRight(payload.Length + (4 - payload.Length % 4) % 4, '=');

        var json = System.Text.Encoding.UTF8.GetString(Convert.FromBase64String(payload));
        using var doc = JsonDocument.Parse(json);

        // ASP.NET Core serialises ClaimTypes.NameIdentifier as "nameid" in short-form JWTs
        // but sometimes as the full URI
        foreach (var key in new[]
        {
            "nameid",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier",
            "sub"
        })
        {
            if (doc.RootElement.TryGetProperty(key, out var v))
                return v.GetString();
        }
        return null;
    }
    catch { return null; }
}

static void Banner(string text)
{
    var line = new string('─', text.Length + 4);
    Console.WriteLine(line);
    Console.WriteLine($"  {text}");
    Console.WriteLine(line);
    Console.WriteLine();
}

static void Ok(string msg)
{
    Console.ForegroundColor = ConsoleColor.Green;
    Console.WriteLine($"[OK]    {msg}");
    Console.ResetColor();
}

static void Warn(string msg)
{
    Console.ForegroundColor = ConsoleColor.Yellow;
    Console.WriteLine($"[WARN]  {msg}");
    Console.ResetColor();
}

static void Error(string msg)
{
    Console.ForegroundColor = ConsoleColor.Red;
    Console.WriteLine($"[ERROR] {msg}");
    Console.ResetColor();
}

static string ReadPassword()
{
    var sb = new System.Text.StringBuilder();
    while (true)
    {
        var key = Console.ReadKey(intercept: true);
        if (key.Key == ConsoleKey.Enter)
        {
            Console.WriteLine();
            break;
        }
        if (key.Key == ConsoleKey.Backspace && sb.Length > 0)
        {
            sb.Remove(sb.Length - 1, 1);
            Console.Write("\b \b");
        }
        else if (key.Key != ConsoleKey.Backspace)
        {
            sb.Append(key.KeyChar);
            Console.Write('*');
        }
    }
    return sb.ToString();
}
