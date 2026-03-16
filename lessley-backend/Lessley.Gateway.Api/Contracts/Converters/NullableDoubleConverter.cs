using System.Text.Json;
using System.Text.Json.Serialization;

namespace Lessley.Gateway.Api.Contracts.Converters
{
    /// <summary>
    /// Custom JSON converter that handles deserializing string or number values to nullable double.
    /// Empty strings are converted to null.
    /// </summary>
    public class NullableDoubleConverter : JsonConverter<double?>
    {
        public override double? Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            switch (reader.TokenType)
            {
                case JsonTokenType.Null:
                    return null;

                case JsonTokenType.String:
                    var stringValue = reader.GetString();
                    if (string.IsNullOrWhiteSpace(stringValue))
                        return null;

                    if (double.TryParse(stringValue, out var doubleValue))
                        return doubleValue;

                    throw new JsonException($"Unable to convert \"{stringValue}\" to double.");

                case JsonTokenType.Number:
                    return reader.GetDouble();

                default:
                    throw new JsonException($"Unexpected token {reader.TokenType} when parsing double.");
            }
        }

        public override void Write(Utf8JsonWriter writer, double? value, JsonSerializerOptions options)
        {
            if (value.HasValue)
                writer.WriteNumberValue(value.Value);
            else
                writer.WriteNullValue();
        }
    }
}
