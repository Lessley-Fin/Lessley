using Lessley.Gateway.Api.Models.DealSearch;
using MongoDB.Bson;
using MongoDB.Bson.Serialization;
using MongoDB.Driver;
using Xunit;

namespace Lessley.Gateway.Tests;

/// <summary>
/// Binding the scraping pipeline's own <c>deals</c>/<c>stores</c> documents.
///
/// Deal search reads those collections directly — the same ones the scraper writes and
/// deal-optimizer and Personalization read. Every conversion they need (business key,
/// ISO-string timestamps, flattened display fields) therefore lives in the DTOs, and these
/// tests are what keep it faithful to the shapes actually stored.
/// </summary>
public class DealDocumentMappingTests
{
    /// <summary>A deal exactly as DealMongoRepository.save writes it.</summary>
    private static BsonDocument RawDeal() => new()
    {
        // The business key is _id itself, not an ObjectId alongside an `id` field.
        { "_id", "019fb89cf6ec_07bb8f521accc3ee" },
        { "store_id", "019fa450b45f_a72fea74db71995a" },
        { "raw_id", "019fb6dd37e2_9d02047ea846bb87" },
        { "source_id", "hever_gift_card_company" },
        // ISO strings, not BSON dates — Python's to_dict emits text.
        { "scraped_at", "2026-07-31T06:29:38.914324+00:00" },
        { "resolved_at", "2026-07-31T14:38:42.411776+00:00" },
        { "title", "SHASHA GIFTS" },
        { "deal_description", "gift cards" },
        { "club_id", "club_hever" },
        { "currency", "ILS" },
        { "url", "https://www.shashagifts.com" },
        { "deal_type", "giftcard_discount" },
        { "terms_and_conditions", "Up to 3,000 ILS per month." },
        { "discount_logic", new BsonDocument
            {
                { "type", "percentage" },
                { "condition", new BsonDocument { { "type", "min_quantity" }, { "value", 1 } } },
                { "reward", new BsonDocument
                    {
                        { "type", "percentage_off" },
                        { "value", 0.3 },
                        { "max_discount_amount", 300 },
                    }
                },
            }
        },
        { "constraints", new BsonDocument
            {
                { "limits", new BsonDocument
                    {
                        { "minimum_purchase", 100 },
                        { "max_uses_per_transaction", 2 },
                        { "max_uses_per_month", BsonNull.Value },
                    }
                },
                { "eligibility", new BsonDocument { { "membership_required", true } } },
                { "redemption_channels", new BsonDocument
                    {
                        { "website", "yes" },
                        { "physical_store", "no" },
                    }
                },
            }
        },
        // Storage-level field the DTO must ignore rather than choke on.
        { "fingerprint", "abc123" },
    };

    private static DealDocument Bind(BsonDocument doc) => BsonSerializer.Deserialize<DealDocument>(doc);

    [Fact]
    public void BusinessKeyIsReadFromUnderscoreId()
    {
        // The shape DealMongoRepository.save writes.
        Assert.Equal("019fb89cf6ec_07bb8f521accc3ee", Bind(RawDeal()).DealId);
    }

    [Fact]
    public void BusinessKeyIsReadFromIdWhenUnderscoreIdIsAnObjectId()
    {
        // The shape mongoimport produces from main/resources/deals.json: the business key
        // stays in `id` and Mongo generates an ObjectId `_id`. Binding _id as a plain
        // string threw here, which is what took Personalization down at startup.
        var doc = RawDeal();
        doc["_id"] = ObjectId.GenerateNewId();
        doc["id"] = "019fe3627cbe_3f1efa9755ca8314";

        var deal = Bind(doc);

        Assert.Equal("019fe3627cbe_3f1efa9755ca8314", deal.DealId);
        // Everything else still binds off the same document.
        Assert.Equal("SHASHA GIFTS", deal.Title);
        Assert.Equal(0.3, deal.Discount.PercentOff);
    }

    [Fact]
    public void StoreBusinessKeyIsReadFromIdWhenUnderscoreIdIsAnObjectId()
    {
        var doc = new BsonDocument
        {
            { "_id", ObjectId.GenerateNewId() },
            { "id", "019d2090d408_04f0484327138601" },
            { "name", "KSP" },
            { "metadata", new BsonDocument { { "mcc_codes", new BsonArray { "GROCERIES" } } } },
        };

        var store = BsonSerializer.Deserialize<StoreDocument>(doc);

        Assert.Equal("019d2090d408_04f0484327138601", store.StoreId);
        Assert.Equal("KSP", store.Name);
    }

    [Fact]
    public void TheRawKeyFieldsStayOutOfTheJsonContract()
    {
        // The SPA's DealDocument type has dealId and no mongoId/businessId; the two raw
        // fields exist only to resolve the key.
        var doc = RawDeal();
        doc["_id"] = ObjectId.GenerateNewId();
        doc["id"] = "deal_42";

        // Web defaults = camelCase, i.e. what ASP.NET Core actually emits for a controller.
        var json = System.Text.Json.JsonSerializer.Serialize(
            Bind(doc), new System.Text.Json.JsonSerializerOptions(System.Text.Json.JsonSerializerDefaults.Web));

        Assert.Contains("\"dealId\":\"deal_42\"", json);
        Assert.DoesNotContain("mongoId", json);
        Assert.DoesNotContain("businessId", json);
        // The raw sub-documents are not part of the contract either — the client gets the
        // flattened view, and their BsonValue members throw when System.Text.Json walks them.
        Assert.DoesNotContain("discountLogic", json);
        Assert.DoesNotContain("constraints", json);
        // What the SPA actually reads survives.
        Assert.Contains("\"percentOff\":0.3", json);
        Assert.Contains("\"redeemChannels\":[\"website\"]", json);
        Assert.Contains("\"membershipRequired\":true", json);
    }

    [Fact]
    public void IsoStringTimestampsBind()
    {
        var deal = Bind(RawDeal());

        Assert.Equal(new DateTime(2026, 7, 31, 6, 29, 38, DateTimeKind.Utc), deal.ScrapedAt, TimeSpan.FromSeconds(1));
        Assert.NotNull(deal.ResolvedAt);
        Assert.Equal(new DateTime(2026, 7, 31, 14, 38, 42, DateTimeKind.Utc), deal.ResolvedAt!.Value, TimeSpan.FromSeconds(1));
    }

    [Fact]
    public void RealBsonDatesAlsoBind()
    {
        // Rows written by mongoimport/Compass carry real dates; both shapes must work.
        var doc = RawDeal();
        doc["scraped_at"] = new BsonDateTime(new DateTime(2026, 7, 31, 6, 29, 38, DateTimeKind.Utc));

        Assert.Equal(new DateTime(2026, 7, 31, 6, 29, 38, DateTimeKind.Utc), Bind(doc).ScrapedAt);
    }

    [Fact]
    public void MissingResolvedAtIsNull()
    {
        var doc = RawDeal();
        doc["resolved_at"] = BsonNull.Value;

        Assert.Null(Bind(doc).ResolvedAt);
    }

    [Fact]
    public void PercentageRewardFlattensIntoPercentOffOnly()
    {
        // The reward's *type* decides which of the three value fields is populated, so a
        // badge can tell "30% off" from "30 ILS off" from "pay 30 ILS".
        var discount = Bind(RawDeal()).Discount;

        Assert.Equal("percentage_off", discount.RewardType);
        Assert.Equal(0.3, discount.PercentOff);
        Assert.Null(discount.AmountOff);
        Assert.Null(discount.FixedPrice);
        Assert.Equal(300, discount.MaxDiscountAmount);
    }

    [Theory]
    [InlineData("fixed_discount_amount")]
    [InlineData("fixed_total_amount")]
    public void OtherRewardTypesLandInTheirOwnField(string rewardType)
    {
        var doc = RawDeal();
        doc["discount_logic"]["reward"]["type"] = rewardType;
        doc["discount_logic"]["reward"]["value"] = 50;

        var discount = Bind(doc).Discount;

        Assert.Null(discount.PercentOff);
        Assert.Equal(50, rewardType == "fixed_discount_amount" ? discount.AmountOff : discount.FixedPrice);
    }

    [Theory]
    [InlineData("min_spend", 100d, 100d, null)]
    [InlineData("exact_spend", 100d, 100d, null)]
    [InlineData("min_quantity", 3d, null, 3d)]
    public void ConditionSplitsBySpendVersusQuantity(
        string conditionType, double value, double? expectedMinSpend, double? expectedMinQuantity)
    {
        var doc = RawDeal();
        doc["discount_logic"]["condition"]["type"] = conditionType;
        doc["discount_logic"]["condition"]["value"] = value;

        var discount = Bind(doc).Discount;

        Assert.Equal(expectedMinSpend, discount.MinSpend);
        Assert.Equal(expectedMinQuantity, discount.MinQuantity);
    }

    [Fact]
    public void LimitsAreLiftedOutOfConstraints()
    {
        var limits = Bind(RawDeal()).Limits;

        Assert.Equal(100, limits.MinimumPurchase);
        Assert.Equal(2, limits.MaxUsesPerTransaction);
        Assert.Null(limits.MaxUsesPerMonth);
    }

    [Fact]
    public void OnlyAvailableRedemptionChannelsAreListed()
    {
        Assert.Equal(["website"], Bind(RawDeal()).RedeemChannels);
    }

    [Fact]
    public void RedemptionChannelsMayAlsoBeABareList()
    {
        var doc = RawDeal();
        doc["constraints"]["redemption_channels"] = new BsonArray { "website", "physical_store" };

        Assert.Equal(["website", "physical_store"], Bind(doc).RedeemChannels);
    }

    [Theory]
    [InlineData(true, true)]
    [InlineData(false, false)]
    public void MembershipRequiredReadsABool(bool stored, bool expected)
    {
        var doc = RawDeal();
        doc["constraints"]["eligibility"]["membership_required"] = stored;

        Assert.Equal(expected, Bind(doc).MembershipRequired);
    }

    [Fact]
    public void MembershipRequiredAlsoReadsYesNoText()
    {
        var doc = RawDeal();
        doc["constraints"]["eligibility"]["membership_required"] = "yes";

        Assert.True(Bind(doc).MembershipRequired);
    }

    [Fact]
    public void ADealWithoutConstraintsOrDiscountStillBinds()
    {
        // Deals scraped before the constraints stage existed carry neither sub-document;
        // they must render as "no terms known", not fail the whole search.
        var doc = RawDeal();
        doc.Remove("constraints");
        doc.Remove("discount_logic");

        var deal = Bind(doc);

        Assert.Empty(deal.RedeemChannels);
        Assert.Null(deal.MembershipRequired);
        Assert.Null(deal.Discount.RewardType);
        Assert.Null(deal.Limits.MinimumPurchase);
    }

    [Fact]
    public void NullClubIdIsTolerated()
    {
        // Rows predating PersistStage's source -> club map; `deals backfill-club-ids` fills them.
        var doc = RawDeal();
        doc["club_id"] = BsonNull.Value;

        Assert.Null(Bind(doc).ClubId);
    }

    [Fact]
    public void StoreBindsFromThePipelineShape()
    {
        var doc = new BsonDocument
        {
            { "_id", "019d2090d408_04f0484327138601" },
            { "name", "KSP" },
            { "name_forms", new BsonDocument { { "normalized", "ksp" } } },
            { "created_at", "2026-03-24T15:57:35.623387+00:00" },
            { "metadata", new BsonDocument
                {
                    { "mcc_codes", new BsonArray { "GROCERIES", "PHARMACY" } },
                    { "store_url", "https://ksp.co.il" },
                    { "image_urls", new BsonArray { "https://cdn/1.png" } },
                }
            },
        };

        var store = BsonSerializer.Deserialize<StoreDocument>(doc);

        Assert.Equal("019d2090d408_04f0484327138601", store.StoreId);
        Assert.Equal("KSP", store.Name);
        Assert.Equal(["GROCERIES", "PHARMACY"], store.Metadata.MccCodes);
        Assert.Equal("https://ksp.co.il", store.Metadata.StoreUrl);
    }

    /// <summary>
    /// Deal search does not just deserialize these documents, it builds queries against them.
    /// A custom serializer that cannot report its item type renders no array operator, which
    /// surfaces as a 500 on every MCC-filtered search rather than a binding error — so the
    /// filters are rendered here, not just the documents bound.
    /// </summary>
    [Fact]
    public void TheMccFilterCanBeRendered()
    {
        var filter = Builders<StoreDocument>.Filter.AnyIn(s => s.Metadata.MccCodes, ["GROCERIES", "PHARMACY"]);

        var rendered = Render(filter);

        Assert.Contains("metadata.mcc_codes", rendered.ToString());
        Assert.Contains("GROCERIES", rendered.ToString());
    }

    [Fact]
    public void TheDealStoreJoinFilterCanBeRendered()
    {
        var filter = Builders<DealDocument>.Filter.In(d => d.StoreId, ["store_1", "store_2"]);

        Assert.Contains("store_id", Render(filter).ToString());
    }

    [Fact]
    public void TheTimestampBackedFieldsDoNotBreakRendering()
    {
        // The flexible DateTime serializer is used on a filtered-on document, so make sure a
        // comparison against it renders too.
        var filter = Builders<DealDocument>.Filter.Gt(d => d.ScrapedAt, new DateTime(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc));

        Assert.Contains("scraped_at", Render(filter).ToString());
    }

    private static BsonDocument Render<T>(FilterDefinition<T> filter) =>
        filter.Render(new RenderArgs<T>(
            BsonSerializer.SerializerRegistry.GetSerializer<T>(), BsonSerializer.SerializerRegistry));

    [Fact]
    public void LegacyNumericMccCodesBindAsStrings()
    {
        // Pre-catalogue rows hold the raw 4-digit MCC as a number; the old projection
        // stringified them on the way out. One such row must not break the store query.
        var doc = new BsonDocument
        {
            { "_id", "store_1" },
            { "name", "Legacy" },
            { "metadata", new BsonDocument { { "mcc_codes", new BsonArray { 5411, "GROCERIES" } } } },
        };

        var store = BsonSerializer.Deserialize<StoreDocument>(doc);

        Assert.Equal(["5411", "GROCERIES"], store.Metadata.MccCodes);
    }
}
