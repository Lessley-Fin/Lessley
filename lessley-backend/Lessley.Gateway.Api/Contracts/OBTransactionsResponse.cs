using System.Text.Json.Serialization;
using Lessley.Gateway.Api.Contracts.Converters;

namespace Lessley.Gateway.Api.Contracts
{
    public class OBTransactionsResponse
    {
        [JsonPropertyName("nextPage")]
        public string? NextPage { get; set; }

        [JsonPropertyName("items")]
        public List<OBTransaction> Items { get; set; } = [];
    }

    public class OBTransaction
    {
        public string? Id { get; set; }
        public string? UserId { get; set; }
        public string? ProviderId { get; set; }
        public string? AccountId { get; set; }
        public string? AccountNumber { get; set; }
        public string? Status { get; set; }
        public string? CategoryCode { get; set; }

        public OBTransactionAmount? Amount { get; set; }
        public OBTransactionDescription? Description { get; set; }
        public OBTransactionCategory? Category { get; set; }

        public string? Type { get; set; }
        public OBTransactionDates? Date { get; set; }

        public OBMerchantAddress? MerchantAddress { get; set; }
        public string? MerchantName { get; set; }
    }

    public class OBTransactionAmount
    {
        public OBAmountDetail? OriginalAmount { get; set; }
        public OBAmountDetail? ChargedAmount { get; set; }
    }

    public class OBAmountDetail
    {
        [JsonConverter(typeof(NullableDoubleConverter))]
        public double? Amount { get; set; }
        public string? Currency { get; set; }
    }

    public class OBTransactionDescription
    {
        public string? Description { get; set; }
        public string? AdditionalInfo { get; set; }
    }

    public class OBTransactionCategory
    {
        public string? Main { get; set; }
        public string? Sub { get; set; }
    }

    public class OBInstallments
    {
        public int? Number { get; set; }
        public int? Total { get; set; }
    }

    public class OBTransactionDates
    {
        public DateTime? ValueDate { get; set; }
        public DateTime? BookingDate { get; set; }
        public DateTime? TransactionDate { get; set; }
    }

    public class OBMerchantAddress
    {
        public string? StreetName { get; set; }
        public uint? BuildingNumber { get; set; }
        public string? TownName { get; set; }
        public uint? PostCode { get; set; }
        public string? Country { get; set; }
    }

    public class OBAccountInfo
    {
        public string? Iban { get; set; }
        public string? Bban { get; set; }
        public string? MaskedPan { get; set; }
        public string? Msisdn { get; set; }
        public string? Currency { get; set; }
        public string? Other { get; set; }
        public string? CashAccountType { get; set; }
    }

    public class OBTransactionSecurityDetails
    {
        [JsonConverter(typeof(NullableDoubleConverter))]
        public double? UnitsNumber { get; set; }
        public OBAmountDetail? UnitsNominal { get; set; }
    }
}
