using System.Text.Json.Serialization;

namespace Lessley.Gateway.Api.Contracts
{
    public class ConnectionResponse
    {
        [JsonPropertyName("connectUrl")]
        public string ConnectUrl { get; set; } = "";

        [JsonPropertyName("connectionId")]
        public string ConnectionId { get; set; } = "";
    }
}
