using System.Text.Json.Serialization;

namespace Lessley.Gateway.Api.Contracts
{
    /// <summary>One bank connection as Open Finance lists it.</summary>
    /// <remarks>
    /// Both id spellings are accepted: the connection-creation response calls it
    /// <c>connectionId</c> (see <see cref="ConnectionResponse"/>), while collection endpoints
    /// tend to return the plain <c>id</c>. Taking either means a change on their side to the
    /// one we don't expect still yields a usable identifier instead of a silent no-op delete.
    /// </remarks>
    public class OpenFinanceConnection
    {
        [JsonPropertyName("id")]
        public string? Id { get; set; }

        [JsonPropertyName("connectionId")]
        public string? ConnectionId { get; set; }

        [JsonIgnore]
        public string? Identifier => !string.IsNullOrWhiteSpace(Id) ? Id : ConnectionId;
    }

    /// <summary>The paged envelope Open Finance wraps its collections in.</summary>
    public class OpenFinanceConnectionsResponse
    {
        [JsonPropertyName("items")]
        public List<OpenFinanceConnection> Items { get; set; } = new();
    }
}
