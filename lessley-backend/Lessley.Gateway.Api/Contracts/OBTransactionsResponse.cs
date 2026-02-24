namespace Lessley.Gateway.Api.Contracts
{
    using System;
    using System.Collections.Generic;
    using System.Text.Json.Serialization;

    public class OBTransactionsResponse
    {
        [JsonPropertyName("nextPage")]
        public string? NextPage { get; set; }

        [JsonPropertyName("items")]
        public List<OBTransaction> Items { get; set; } = new List<OBTransaction>();
    }

    public class OBTransaction
    {
        public string? Id { get; set; }
        public string? SK { get; set; }
        public string? UserId { get; set; }
        public string? OrgId { get; set; }
        public string? ConnectionId { get; set; }
        public string? AccountId { get; set; }
        public string? ProviderId { get; set; }
        public string? TransactionProviderIdentifier { get; set; }
        public string? RelatedPaymentId { get; set; }
        public string? AccountNumber { get; set; }
        public string? Status { get; set; }
        public string? EntryReference { get; set; }
        public string? CategoryCode { get; set; }

        public OBTransactionSecurityDetails? SecurityDetails { get; set; }

        public OBTransactionAmount? Amount { get; set; }
        public OBTransactionDescription? Description { get; set; }
        public OBTransactionCategory? Category { get; set; }
        public OBTransactionCategory? ChangedCategory { get; set; }
        public OBInstallments? Installments { get; set; }

        public string? Type { get; set; }
        public OBTransactionDates? Date { get; set; }

        public OBMerchantAddress? MerchantAddress { get; set; }
        public string? MerchantName { get; set; }
        public string? Details { get; set; }

        public bool? IsInvoiced { get; set; }
        public string? Code { get; set; }
        public bool? IsDuplicate { get; set; }
        public double? BalancePerEndDay { get; set; }

        public OBAccountInfo? CreditorAccount { get; set; }
        public OBAccountInfo? DebtorAccount { get; set; }

        public string? EndToEndId { get; set; }
    }

    public class OBTransactionAmount
    {
        public OBAmountDetail? OriginalAmount { get; set; }
        public OBAmountDetail? ChargedAmount { get; set; }
    }

    public class OBAmountDetail
    {
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
        public string? BuildingNumber { get; set; }
        public string? TownName { get; set; }
        public string? PostCode { get; set; }
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
        public double? UnitsNumber { get; set; }
        public OBAmountDetail? UnitsNominal { get; set; }
    }

}
