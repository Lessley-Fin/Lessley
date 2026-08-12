using MongoDB.Bson;
using MongoDB.Bson.Serialization;
using MongoDB.Bson.Serialization.Serializers;

namespace Lessley.Gateway.Api.Data;

/// <summary>
/// Reads a <see cref="DateTime"/> that may be stored either as a BSON date or as an ISO-8601
/// string.
/// </summary>
/// <remarks>
/// The pipeline's own collections (<c>deals</c>, written by <c>DealMongoRepository</c>) keep
/// timestamps as ISO strings, because that is what Python's <c>to_dict</c> emits. The driver
/// binds a BSON date to <c>DateTime</c> and nothing else, so reading those rows directly —
/// rather than through the projection that used to convert them — needs this.
///
/// Both shapes are accepted rather than just the string one: the same documents are also
/// imported by tools (mongoimport, Compass) that write real dates, and a future pipeline
/// change to emit BSON dates must not require a matching change here.
/// </remarks>
public class FlexibleDateTimeSerializer : SerializerBase<DateTime>
{
    public override DateTime Deserialize(BsonDeserializationContext context, BsonDeserializationArgs args)
    {
        var reader = context.Reader;

        switch (reader.GetCurrentBsonType())
        {
            case BsonType.DateTime:
                // The driver's own reader hands back UTC milliseconds since the epoch.
                return BsonUtils.ToDateTimeFromMillisecondsSinceEpoch(reader.ReadDateTime());

            case BsonType.String:
                var text = reader.ReadString();
                return DateTime.TryParse(
                    text,
                    null,
                    System.Globalization.DateTimeStyles.AdjustToUniversal | System.Globalization.DateTimeStyles.AssumeUniversal,
                    out var parsed)
                    ? parsed
                    // An unparseable timestamp is not worth failing a whole search over; the
                    // Python projection logged and nulled it, and default(DateTime) is the
                    // closest equivalent for a non-nullable property.
                    : default;

            case BsonType.Null:
                reader.ReadNull();
                return default;

            default:
                throw new FormatException(
                    $"Cannot deserialize a DateTime from BsonType {reader.GetCurrentBsonType()}.");
        }
    }

    public override void Serialize(BsonSerializationContext context, BsonSerializationArgs args, DateTime value)
        => context.Writer.WriteDateTime(BsonUtils.ToMillisecondsSinceEpoch(value));
}

/// <summary>Nullable counterpart of <see cref="FlexibleDateTimeSerializer"/>.</summary>
public class FlexibleNullableDateTimeSerializer : SerializerBase<DateTime?>
{
    private static readonly FlexibleDateTimeSerializer Inner = new();

    public override DateTime? Deserialize(BsonDeserializationContext context, BsonDeserializationArgs args)
    {
        if (context.Reader.GetCurrentBsonType() == BsonType.Null)
        {
            context.Reader.ReadNull();
            return null;
        }

        return Inner.Deserialize(context, args);
    }

    public override void Serialize(BsonSerializationContext context, BsonSerializationArgs args, DateTime? value)
    {
        if (value is null) context.Writer.WriteNull();
        else Inner.Serialize(context, args, value.Value);
    }
}

/// <summary>
/// Reads an <c>_id</c> that may be an ObjectId or a string, always as a string.
/// </summary>
/// <remarks>
/// The pipeline's repositories pop the business key into <c>_id</c>, so a scraped row's
/// <c>_id</c> is a string. Rows loaded with <c>mongoimport</c> from
/// <c>main/resources/*.json</c> keep their business key in <c>id</c> and get a generated
/// ObjectId <c>_id</c> instead. Both shapes exist in live databases, and binding <c>_id</c>
/// as a plain string throws on the imported ones — which is a 500 on every deal search
/// rather than a degraded result.
/// </remarks>
public class FlexibleIdSerializer : SerializerBase<string>
{
    public override string Deserialize(BsonDeserializationContext context, BsonDeserializationArgs args)
    {
        var reader = context.Reader;

        switch (reader.GetCurrentBsonType())
        {
            case BsonType.String:   return reader.ReadString();
            case BsonType.ObjectId: return reader.ReadObjectId().ToString();
            case BsonType.Null:     reader.ReadNull(); return "";
            default:                reader.SkipValue(); return "";
        }
    }

    public override void Serialize(BsonSerializationContext context, BsonSerializationArgs args, string value)
    {
        // Written back as whatever it parses as, so a round-trip does not change the key's
        // type. Nothing in the Gateway writes these collections today.
        if (ObjectId.TryParse(value, out var objectId)) context.Writer.WriteObjectId(objectId);
        else context.Writer.WriteString(value ?? "");
    }
}

/// <summary>
/// Reads a list of strings whose elements may not all be strings on disk.
/// </summary>
/// <remarks>
/// <c>metadata.mcc_codes</c> holds canonical category names ("GROCERIES") today, but rows
/// written before that convention still carry the raw 4-digit MCC as a **number**. The
/// projection stringified them on the way out; reading <c>stores</c> directly means doing it
/// here instead. One legacy row would otherwise throw and take the whole store query with it.
/// </remarks>
/// <remarks>
/// Implements <see cref="IBsonArraySerializer"/> because the deal search filters this field
/// with <c>AnyIn</c>: rendering an array operator needs the item serialization info, and
/// without it the driver throws "must implement IBsonArraySerializer" when building the
/// query — a 500 on every MCC-filtered search, not a binding problem.
/// </remarks>
public class FlexibleStringListSerializer : SerializerBase<List<string>>, IBsonArraySerializer
{
    public bool TryGetItemSerializationInfo(out BsonSerializationInfo serializationInfo)
    {
        // Items are always surfaced as strings, whatever they are on disk.
        serializationInfo = new BsonSerializationInfo(
            elementName: null, serializer: new StringSerializer(), nominalType: typeof(string));
        return true;
    }

    public override List<string> Deserialize(BsonDeserializationContext context, BsonDeserializationArgs args)
    {
        var reader = context.Reader;

        if (reader.GetCurrentBsonType() == BsonType.Null)
        {
            reader.ReadNull();
            return [];
        }

        var values = new List<string>();
        reader.ReadStartArray();
        while (reader.ReadBsonType() != BsonType.EndOfDocument)
        {
            switch (reader.GetCurrentBsonType())
            {
                case BsonType.String:  values.Add(reader.ReadString()); break;
                case BsonType.Int32:   values.Add(reader.ReadInt32().ToString()); break;
                case BsonType.Int64:   values.Add(reader.ReadInt64().ToString()); break;
                case BsonType.Double:  values.Add(reader.ReadDouble().ToString(System.Globalization.CultureInfo.InvariantCulture)); break;
                case BsonType.Null:    reader.ReadNull(); break;
                default:               reader.SkipValue(); break;
            }
        }
        reader.ReadEndArray();

        return values;
    }

    public override void Serialize(BsonSerializationContext context, BsonSerializationArgs args, List<string> value)
    {
        context.Writer.WriteStartArray();
        foreach (var item in value ?? []) context.Writer.WriteString(item);
        context.Writer.WriteEndArray();
    }
}
