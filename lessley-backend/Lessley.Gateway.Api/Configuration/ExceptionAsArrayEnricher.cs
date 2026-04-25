using Serilog.Core;
using Serilog.Events;
using System;

namespace Lessley.Gateway.Api.Configuration
{
    public class ExceptionAsArrayEnricher : ILogEventEnricher
    {
        public void Enrich(LogEvent logEvent, ILogEventPropertyFactory propertyFactory)
        {
            if (logEvent.Exception != null)
            {
                var exceptionDict = new
                {
                    type = logEvent.Exception.GetType().Name,
                    message = logEvent.Exception.Message,
                    traceback = logEvent.Exception.StackTrace?.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries) ?? Array.Empty<string>()
                };

                // destructureObjects: true ensures Serilog formats this as a nested JSON object instead of a flat string
                logEvent.AddPropertyIfAbsent(propertyFactory.CreateProperty("structured_exception", exceptionDict, destructureObjects: true));
            }
        }
    }
}