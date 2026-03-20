using Serilog.Events;
using Serilog.Formatting;
using System.Text.Json;

namespace Lessley.Gateway.Api.Configuration
{
    public class CustomLogFormatter : ITextFormatter
    {
        public void Format(LogEvent logEvent, TextWriter output)
        {
            var logRecord = new Dictionary<string, object?>
            {
                { "app_name", "gateway" },
                { "service_name", logEvent.Properties.TryGetValue("SourceContext", out var sc) ? sc.ToString().Trim('"') : "Unknown" },
                { "username", logEvent.Properties.TryGetValue("username", out var un) ? un.ToString().Trim('"') : "anonymous" },
                { "request_id", logEvent.Properties.TryGetValue("request_id", out var rid) ? rid.ToString().Trim('"') : "N/A" },
                { "message", logEvent.RenderMessage() },
                { "exception", logEvent.Exception?.ToString() },
                { "timestamp", logEvent.Timestamp.UtcDateTime.ToString("o") }
            };

            output.WriteLine(JsonSerializer.Serialize(logRecord));
        }
    }
}