#nullable enable

using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using IJT_CSharp_Client.Client;
using Microsoft.Extensions.Logging;
using Opc.Ua;
using UAModel.IJTBase;
using UAModel.MachineryResult;

namespace IJT_CSharp_Client.Helpers;

/// <summary>
/// JSON serializer for IJT / OPC UA data types.
/// Handles OPC UA special types (LocalizedText, NodeId, StatusCode, ExtensionObject, Variant, etc.)
/// and produces human-readable indented JSON for console diagnostics.
/// </summary>
public static class IjtJsonSerializer
{
    private static readonly JsonSerializerOptions _opts = new()
    {
        WriteIndented                = true,
        DefaultIgnoreCondition       = JsonIgnoreCondition.WhenWritingNull,
        ReferenceHandler             = ReferenceHandler.IgnoreCycles,
        Converters =
        {
            new JsonStringEnumConverter(),          // enums as strings (e.g. "OK" not 0)
            new LocalizedTextConverter(),
            new NodeIdConverter(),
            new ExpandedNodeIdConverter(),
            new StatusCodeConverter(),
            new ExtensionObjectConverter(),
            new VariantConverter(),
            new QualifiedNameConverter(),
            new EUInformationConverter(),
            new UuidConverter(),
        },
    };

    private static readonly ILogger _log = IjtLog.ForCategory("IJT.JsonSerializer");

    /// <summary>
    /// Serializes any value to indented JSON.
    /// ExtensionObject bodies and Variants are unwrapped automatically.
    /// </summary>
    public static string Serialize(object? value)
    {
        if (value is null) return "null";

        // Unwrap ExtensionObject transparently
        if (value is ExtensionObject eo)
        {
            if (eo.Body is null)
                return $"\"(empty ExtensionObject, TypeId={eo.TypeId})\"";
            return Serialize(eo.Body);
        }

        // Unwrap Variant
        if (value is Variant v)
            return v.Value is null ? "null" : Serialize(v.Value);

        // Unwrap ExtensionObject arrays
        if (value is ExtensionObject[] eoArr)
        {
            var items = eoArr.Select(x => x.Body ?? (object)$"(empty, TypeId={x.TypeId})").ToArray();
            return JsonSerializer.Serialize(items, items.GetType(), _opts);
        }

        try
        {
            return JsonSerializer.Serialize(value, value.GetType(), _opts);
        }
        catch (Exception ex)
        {
            return JsonSerializer.Serialize(
                new { _type = value.GetType().Name, _serializeError = ex.Message }, _opts);
        }
    }

    /// <summary>
    /// Prints a labeled JSON block to the logger with a box border.
    /// </summary>
    public static void Print(string label, object? value)
    {
        var sb = new StringBuilder();
        AppendJsonBlock(sb, label, value);
        _log.LogInformation("{Output}", sb.ToString().TrimEnd());
    }

    private static void AppendJsonBlock(StringBuilder sb, string label, object? value)
    {
        sb.AppendLine($"  ┌── {label}");
        var json = Serialize(value);
        foreach (var line in json.Split('\n'))
            sb.AppendLine($"  │  {line.TrimEnd()}");
        sb.AppendLine("  └──");
    }

    /// <summary>
    /// Prints all output arguments from an OPC UA method call as labeled JSON blocks.
    /// Uses structured formatting for ResultDataType values.
    /// </summary>
    public static void PrintMethodOutputs(string methodName, IList<object> outputs)
    {
        if (outputs.Count == 0)
        {
            _log.LogInformation("[{Method}] No output arguments.", methodName);
            return;
        }
        _log.LogInformation("── {Method} ──", methodName);
        for (int i = 0; i < outputs.Count; i++)
        {
            var val = outputs[i] is Variant vt ? vt.Value : outputs[i];
            if (val is ResultDataType ||
                (val is ExtensionObject eo && eo.Body is ResultDataType))
                PrintResult(val);
            else
                Print($"output[{i}]", outputs[i]);
        }
    }

    /// <summary>
    /// Prints a ResultDataType with full structured formatting.
    /// ResultMetaData shows all 33 properties; ResultContent is printed as JSON.
    /// </summary>
    public static void PrintResult(object? result)
    {
        if (result is null) { _log.LogInformation("(null result)"); return; }

        var value = result is ExtensionObject eo ? eo.Body ?? result : result;
        value = value is Variant v ? v.Value ?? value : value;

        if (value is ResultDataType rd)
        {
            PrintStructuredResult(rd);
            return;
        }

        Print("Result", value);
    }

    private static void PrintStructuredResult(ResultDataType rd)
    {
        var sb = new StringBuilder();
        sb.AppendLine();
        sb.AppendLine("  RESULT");
        sb.AppendLine("  ├── ResultMetaData");
        AppendAllMetaDataFields(sb, rd.ResultMetaData);
        sb.AppendLine("  └── ResultContent");
        if (rd.ResultContent != null && rd.ResultContent.Count > 0)
            foreach (var item in rd.ResultContent)
                AppendJsonBlock(sb, "        item", item);
        else
            sb.AppendLine("        (no result content)");
        _log.LogInformation("{Output}", sb.ToString().TrimEnd());
    }

    /// <summary>Prints ALL fields from ResultMetaDataType base + JoiningResultMetaDataType subtype.</summary>
    private static void AppendAllMetaDataFields(StringBuilder sb, ResultMetaDataType? meta)
    {
        if (meta is null) { sb.AppendLine("        (no metadata)"); return; }

        // ── Base ResultMetaDataType fields ────────────────────────────────────
        AppendMetaField(sb, "ResultId",                  meta.ResultId);
        AppendMetaField(sb, "HasTransferableDataOnFile", meta.HasTransferableDataOnFile.ToString());
        AppendMetaField(sb, "IsPartial",                 meta.IsPartial.ToString());
        AppendMetaField(sb, "IsSimulated",               meta.IsSimulated.ToString());
        AppendMetaField(sb, "ResultState",               meta.ResultState.ToString());
        AppendMetaField(sb, "StepId",                    meta.StepId);
        AppendMetaField(sb, "PartId",                    meta.PartId);
        AppendMetaField(sb, "ExternalRecipeId",          meta.ExternalRecipeId);
        AppendMetaField(sb, "InternalRecipeId",          meta.InternalRecipeId);
        AppendMetaField(sb, "ProductId",                 meta.ProductId);
        AppendMetaField(sb, "ExternalConfigurationId",   meta.ExternalConfigurationId);
        AppendMetaField(sb, "InternalConfigurationId",   meta.InternalConfigurationId);
        AppendMetaField(sb, "JobId",                     meta.JobId);
        AppendMetaField(sb, "CreationTime",
            meta.CreationTime > DateTime.MinValue
                ? meta.CreationTime.ToString("yyyy-MM-dd HH:mm:ss.fff UTC")
                : null);
        if (meta.ProcessingTimes != null)
            AppendJsonBlock(sb, "        ProcessingTimes", meta.ProcessingTimes);
        AppendMetaField(sb, "ResultUri",
            meta.ResultUri?.Count > 0 ? string.Join(", ", meta.ResultUri) : null);
        AppendMetaField(sb, "ResultEvaluation",          meta.ResultEvaluation.ToString());
        AppendMetaField(sb, "ResultEvaluationCode",
            meta.ResultEvaluationCode != 0 ? meta.ResultEvaluationCode.ToString() : null);
        AppendMetaField(sb, "ResultEvaluationDetails",   meta.ResultEvaluationDetails?.Text);
        AppendMetaField(sb, "FileFormat",
            meta.FileFormat?.Count > 0 ? string.Join(", ", meta.FileFormat) : null);

        // ── JoiningResultMetaDataType extra fields ────────────────────────────
        if (meta is JoiningResultMetaDataType jm)
        {
            AppendMetaField(sb, "JoiningTechnology",   jm.JoiningTechnology?.Text);
            AppendMetaField(sb, "SequenceNumber",      jm.SequenceNumber.ToString());
            AppendMetaField(sb, "Name",                jm.Name);
            AppendMetaField(sb, "Description",         jm.Description?.Text);
            AppendMetaField(sb, "Classification",      jm.Classification.ToString());
            AppendMetaField(sb, "OperationMode",       jm.OperationMode.ToString());
            AppendMetaField(sb, "AssemblyType",        jm.AssemblyType.ToString());
            if (jm.AssociatedEntities?.Count > 0)
                AppendJsonBlock(sb, "        AssociatedEntities", jm.AssociatedEntities);
            if (jm.ResultCounters?.Count > 0)
                AppendJsonBlock(sb, "        ResultCounters", jm.ResultCounters);
            AppendMetaField(sb, "InterventionType",    jm.InterventionType.ToString());
            AppendMetaField(sb, "IsGeneratedOffline",  jm.IsGeneratedOffline.ToString());
            if (jm.ExtendedMetaData?.Count > 0)
                AppendJsonBlock(sb, "        ExtendedMetaData", jm.ExtendedMetaData);
        }
    }

    private static void AppendMetaField(StringBuilder sb, string name, string? value)
    {
        if (string.IsNullOrEmpty(value)) return;
        sb.AppendLine($"      {name,-24} {value}");
    }

    /// <summary>Prints a JoiningSystemEvent with all fields in readable format.</summary>
    public static void PrintJoiningSystemEvent(EventSubscriber.JoiningSystemEventArgs e)
    {
        var sb = new StringBuilder();
        sb.AppendLine();
        sb.AppendLine("  JOINING SYSTEM EVENT");
        sb.AppendLine($"  ├── Time:             {e.EventTime:yyyy-MM-dd HH:mm:ss.fff}");
        sb.AppendLine($"  ├── EventCode:        {e.EventCode}");
        sb.AppendLine($"  ├── EventText:        {e.EventText}");
        sb.Append($"  └── JoiningTechnology:{e.JoiningTechnology}");
        if (e.AllFields.Count > 5)
        {
            sb.AppendLine();
            sb.AppendLine("  Extra fields:");
            foreach (var (k, v) in e.AllFields.Skip(5))
                if (v != null) sb.AppendLine($"       {k,-22} {v}");
        }
        _log.LogInformation("{Output}", sb.ToString().TrimEnd());
    }
}

// ── Custom JSON Converters ─────────────────────────────────────────────────────

internal sealed class LocalizedTextConverter : JsonConverter<LocalizedText>
{
    public override LocalizedText? Read(ref Utf8JsonReader r, Type t, JsonSerializerOptions o)
        => new LocalizedText(r.GetString());
    public override void Write(Utf8JsonWriter w, LocalizedText v, JsonSerializerOptions o)
        => w.WriteStringValue(v?.Text ?? "");
}

internal sealed class NodeIdConverter : JsonConverter<NodeId>
{
    public override NodeId? Read(ref Utf8JsonReader r, Type t, JsonSerializerOptions o)
        => NodeId.Parse(r.GetString() ?? "");
    public override void Write(Utf8JsonWriter w, NodeId v, JsonSerializerOptions o)
        => w.WriteStringValue(v?.ToString() ?? "");
}

internal sealed class ExpandedNodeIdConverter : JsonConverter<ExpandedNodeId>
{
    public override ExpandedNodeId? Read(ref Utf8JsonReader r, Type t, JsonSerializerOptions o)
        => ExpandedNodeId.Parse(r.GetString() ?? "");
    public override void Write(Utf8JsonWriter w, ExpandedNodeId v, JsonSerializerOptions o)
        => w.WriteStringValue(v?.ToString() ?? "");
}

internal sealed class StatusCodeConverter : JsonConverter<StatusCode>
{
    public override StatusCode Read(ref Utf8JsonReader r, Type t, JsonSerializerOptions o)
        => new StatusCode(r.GetUInt32());
    public override void Write(Utf8JsonWriter w, StatusCode v, JsonSerializerOptions o)
        => w.WriteStringValue(v.ToString());
}

internal sealed class ExtensionObjectConverter : JsonConverter<ExtensionObject>
{
    public override ExtensionObject? Read(ref Utf8JsonReader r, Type t, JsonSerializerOptions o)
        => throw new NotSupportedException("ExtensionObject deserialization not supported.");
    public override void Write(Utf8JsonWriter w, ExtensionObject v, JsonSerializerOptions o)
    {
        if (v?.Body is null) { w.WriteNullValue(); return; }
        JsonSerializer.Serialize(w, v.Body, v.Body.GetType(), o);
    }
}

internal sealed class VariantConverter : JsonConverter<Variant>
{
    public override Variant Read(ref Utf8JsonReader r, Type t, JsonSerializerOptions o)
        => throw new NotSupportedException("Variant deserialization not supported.");
    public override void Write(Utf8JsonWriter w, Variant v, JsonSerializerOptions o)
    {
        if (v.Value is null) { w.WriteNullValue(); return; }
        JsonSerializer.Serialize(w, v.Value, v.Value.GetType(), o);
    }
}

internal sealed class QualifiedNameConverter : JsonConverter<QualifiedName>
{
    public override QualifiedName? Read(ref Utf8JsonReader r, Type t, JsonSerializerOptions o)
        => QualifiedName.Parse(r.GetString() ?? "");
    public override void Write(Utf8JsonWriter w, QualifiedName v, JsonSerializerOptions o)
        => w.WriteStringValue(v?.ToString() ?? "");
}

internal sealed class EUInformationConverter : JsonConverter<EUInformation>
{
    public override EUInformation? Read(ref Utf8JsonReader r, Type t, JsonSerializerOptions o)
        => throw new NotSupportedException();
    public override void Write(Utf8JsonWriter w, EUInformation v, JsonSerializerOptions o)
    {
        w.WriteStartObject();
        w.WriteString("DisplayName",   v?.DisplayName?.Text ?? "");
        w.WriteString("Description",   v?.Description?.Text ?? "");
        w.WriteNumber("UnitId",        v?.UnitId ?? 0);
        w.WriteString("NamespaceUri",  v?.NamespaceUri ?? "");
        w.WriteEndObject();
    }
}

internal sealed class UuidConverter : JsonConverter<Uuid>
{
    public override Uuid Read(ref Utf8JsonReader r, Type t, JsonSerializerOptions o)
        => new Uuid(Guid.Parse(r.GetString() ?? Guid.Empty.ToString()));
    public override void Write(Utf8JsonWriter w, Uuid v, JsonSerializerOptions o)
        => w.WriteStringValue(v.GuidString);
}
