using Serilog.Events;
using Serilog.Formatting;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;

namespace Lessley.Gateway.Api.Configuration
{
    public class CustomLogFormatter : ITextFormatter
    {
        // Standard properties that we handle manually so they aren't duplicated in the root
        private static readonly HashSet<string> _standardProperties = new HashSet<string>
        {
            "SourceContext", "username", "request_id", "structured_exception", "app_name", "ActionId", "ActionName", "RequestId", "ConnectionId"
        };

        public void Format(LogEvent logEvent, TextWriter output)
        {
            var logRecord = new Dictionary<string, object?>
            {
                { "timestamp", logEvent.Timestamp.UtcDateTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ") },
                { "level", GetLevelName(logEvent.Level) },
                { "app_name", "gateway" },
                { "service_name", logEvent.Properties.TryGetValue("SourceContext", out var sc) ? UnwrapValue(sc) : "Unknown" },
                { "username", logEvent.Properties.TryGetValue("username", out var un) ? UnwrapValue(un) : "anonymous" },
                { "request_id", logEvent.Properties.TryGetValue("request_id", out var rid) ? UnwrapValue(rid) : "N/A" },
                { "message", logEvent.RenderMessage() }
            };

            // Inject the structured exception array if the enricher created it
            if (logEvent.Properties.TryGetValue("structured_exception", out var structuredException))
            {
                logRecord["exception"] = UnwrapValue(structuredException);
            }
            else if (logEvent.Exception != null)
            {
                logRecord["exception"] = logEvent.Exception.ToString(); // Fallback
            }

            // Dynamically attach any custom fields (like extra_data or reason)
            foreach (var property in logEvent.Properties)
            {
                if (!_standardProperties.Contains(property.Key))
                {
                    logRecord[property.Key] = UnwrapValue(property.Value);
                }
            }

            output.WriteLine(JsonSerializer.Serialize(logRecord));
        }

        private string GetLevelName(LogEventLevel level)
        {
            return level switch
            {
                LogEventLevel.Verbose => "DEBUG",
                LogEventLevel.Debug => "DEBUG",
                LogEventLevel.Information => "INFO",
                LogEventLevel.Warning => "WARNING",
                LogEventLevel.Error => "ERROR",
                LogEventLevel.Fatal => "CRITICAL",
                _ => level.ToString().ToUpper()
            };
        }

        // Recursively unwraps Serilog's internal property structures into standard C# dictionaries/lists for clean JSON serialization
        private object? UnwrapValue(LogEventPropertyValue propertyValue)
        {
            if (propertyValue is ScalarValue scalar) return scalar.Value;
            if (propertyValue is DictionaryValue dict) return dict.Elements.ToDictionary(kvp => kvp.Key.Value?.ToString() ?? "", kvp => UnwrapValue(kvp.Value));
            if (propertyValue is SequenceValue seq) return seq.Elements.Select(UnwrapValue).ToList();
            if (propertyValue is StructureValue str) return str.Properties.ToDictionary(p => p.Name, p => UnwrapValue(p.Value));
            return propertyValue?.ToString();
        }
    }
}