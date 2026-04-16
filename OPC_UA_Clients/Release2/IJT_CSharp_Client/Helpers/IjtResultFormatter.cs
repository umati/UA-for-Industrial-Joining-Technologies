#nullable enable

using System.Globalization;
using System.Text;
using Opc.Ua;
using UAModel.IJTBase;
using UAModel.MachineryResult;

namespace IJT_CSharp_Client.Helpers;

/// <summary>
/// Formats IJT <b>result</b> payloads (ResultDataType) as human-readable text.
/// Covers both <c>JoiningSystemResultReadyEvent</c> and <c>ResultReadyEvent</c> - both
/// carry a <c>ResultDataType</c> (ResultMetaData + ResultContent) as their payload.
/// Returns strings so callers can print to console, write to file, or both.
/// </summary>
public static class IjtResultFormatter
{
    /// <summary>Formats a full ResultDataType into a readable multi-line string.</summary>
    public static string FormatResult(ResultDataType? rd, DateTime eventTime = default)
    {
        if (rd is null) return "(null result)";
        var sb = new StringBuilder();
        var ts = eventTime == default ? DateTime.UtcNow : eventTime;

        sb.AppendLine($"Received: {ts:yyyy-MM-dd HH:mm:ss.fff} UTC");
        sb.AppendLine();
        sb.AppendLine("RESULT");
        sb.AppendLine("  ResultMetaData");
        FormatMetaData(sb, rd.ResultMetaData);
        sb.AppendLine("  ResultContent");
        FormatContent(sb, rd.ResultContent);
        return sb.ToString();
    }

    /// <summary>
    /// Formats result data from individual event fields (used when only event args are available,
    /// not a decoded ResultDataType).
    /// </summary>
    public static string FormatResultEventFields(
        string? resultId,
        string? classification,
        string? name,
        int sequenceNumber,
        string? assemblyType,
        DateTime eventTime)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"Received: {eventTime:yyyy-MM-dd HH:mm:ss.fff} UTC");
        sb.AppendLine();
        sb.AppendLine("RESULT EVENT FIELDS");
        AppendField(sb, "ResultId", resultId);
        AppendField(sb, "Classification", classification);
        AppendField(sb, "Name", name);
        AppendField(sb, "SequenceNumber", sequenceNumber.ToString());
        AppendField(sb, "AssemblyType", assemblyType);
        return sb.ToString();
    }

    // -- private helpers -------------------------------------------------------

    private static void FormatMetaData(StringBuilder sb, ResultMetaDataType? meta)
    {
        if (meta is null) { sb.AppendLine("    (no metadata)"); return; }

        AppendField(sb, "ResultId", meta.ResultId, 4);
        AppendField(sb, "HasTransferableDataOnFile", meta.HasTransferableDataOnFile.ToString(), 4);
        AppendField(sb, "IsPartial", meta.IsPartial.ToString(), 4);
        AppendField(sb, "IsSimulated", meta.IsSimulated.ToString(), 4);
        AppendField(sb, "ResultState", meta.ResultState.ToString(), 4);
        AppendField(sb, "StepId", meta.StepId, 4);
        AppendField(sb, "PartId", meta.PartId, 4);
        AppendField(sb, "ExternalRecipeId", meta.ExternalRecipeId, 4);
        AppendField(sb, "InternalRecipeId", meta.InternalRecipeId, 4);
        AppendField(sb, "ProductId", meta.ProductId, 4);
        AppendField(sb, "ExternalConfigurationId", meta.ExternalConfigurationId, 4);
        AppendField(sb, "InternalConfigurationId", meta.InternalConfigurationId, 4);
        AppendField(sb, "JobId", meta.JobId, 4);
        AppendField(sb, "CreationTime",
            meta.CreationTime > DateTime.MinValue ? meta.CreationTime.ToString("yyyy-MM-dd HH:mm:ss.fff UTC") : null, 4);
        AppendField(sb, "ResultEvaluation", meta.ResultEvaluation.ToString(), 4);
        AppendField(sb, "ResultEvaluationCode",
            meta.ResultEvaluationCode != 0 ? meta.ResultEvaluationCode.ToString() : null, 4);
        AppendField(sb, "ResultEvaluationDetails", meta.ResultEvaluationDetails?.Text, 4);
        AppendField(sb, "ResultUri",
            meta.ResultUri?.Count > 0 ? string.Join(", ", meta.ResultUri) : null, 4);
        AppendField(sb, "FileFormat",
            meta.FileFormat?.Count > 0 ? string.Join(", ", meta.FileFormat) : null, 4);

        // IJT JoiningResultMetaDataType subtype extra fields
        if (meta is UAModel.IJTBase.JoiningResultMetaDataType jm)
        {
            AppendField(sb, "JoiningTechnology", jm.JoiningTechnology?.Text, 4);
            AppendField(sb, "SequenceNumber", jm.SequenceNumber.ToString(), 4);
            AppendField(sb, "Name", jm.Name, 4);
            AppendField(sb, "Description", jm.Description?.Text, 4);
            AppendField(sb, "Classification", jm.Classification.ToString(), 4);
            AppendField(sb, "OperationMode", jm.OperationMode.ToString(), 4);
            AppendField(sb, "AssemblyType", jm.AssemblyType.ToString(), 4);
            AppendField(sb, "InterventionType", jm.InterventionType.ToString(), 4);
            AppendField(sb, "IsGeneratedOffline", jm.IsGeneratedOffline.ToString(), 4);
            if (jm.AssociatedEntities?.Count > 0)
                sb.AppendLine($"    {"AssociatedEntities",-28} ({jm.AssociatedEntities.Count} entities)");
            if (jm.ResultCounters?.Count > 0)
            {
                sb.AppendLine($"    {"ResultCounters",-28} ({jm.ResultCounters.Count} counters)");
                foreach (var c in jm.ResultCounters)
                    sb.AppendLine($"      - {c.Name}: {c.CounterValue}");
            }
            if (jm.ExtendedMetaData?.Count > 0)
            {
                sb.AppendLine($"    {"ExtendedMetaData",-28} ({jm.ExtendedMetaData.Count} entries)");
                foreach (var kv in jm.ExtendedMetaData)
                    sb.AppendLine($"      {kv.Key}: {kv.Value}");
            }
        }
    }

    private static void FormatContent(StringBuilder sb, VariantCollection? content)
    {
        if (content is null || content.Count == 0)
        {
            sb.AppendLine("    (no content)");
            return;
        }
        bool decoded = false;
        foreach (var variant in content)
        {
            var raw = variant.Value is ExtensionObject eo ? eo.Body : variant.Value;
            if (raw is JoiningResultDataType jr)
            {
                FormatJoiningResult(sb, jr);
                decoded = true;
            }
        }
        if (!decoded)
        {
            for (int i = 0; i < content.Count; i++)
                sb.AppendLine($"    [{i}] {content[i]}");
        }
    }

    private static void FormatJoiningResult(StringBuilder sb, JoiningResultDataType jr)
    {
        var mask = (JoiningResultDataTypeFields)jr.EncodingMask;

        var ovs = jr.OverallResultValues;
        sb.AppendLine($"    OverallResultValues ({ovs?.Count ?? 0}):");
        if (ovs?.Count > 0)
            foreach (var rv in ovs)
                FormatResultValue(sb, rv, indent: 6);

        if ((mask & JoiningResultDataTypeFields.StepResults) != 0 && jr.StepResults?.Count > 0)
        {
            sb.AppendLine($"    StepResults ({jr.StepResults.Count}):");
            foreach (var step in jr.StepResults)
            {
                sb.AppendLine($"      Step {step.StepResultId ?? "?",-12} [{step.ResultEvaluation}]  {step.Name}");
                if (step.StepResultValues?.Count > 0)
                    foreach (var rv in step.StepResultValues)
                        FormatResultValue(sb, rv, indent: 8);
            }
        }

        if ((mask & JoiningResultDataTypeFields.Errors) != 0 && jr.Errors?.Count > 0)
        {
            sb.AppendLine($"    Errors ({jr.Errors.Count}):");
            foreach (var err in jr.Errors)
                sb.AppendLine($"      ErrorId={err.ErrorId}  Type={err.ErrorType}  {err.ErrorMessage?.Text}");
        }

        if ((mask & JoiningResultDataTypeFields.FailureReason) != 0 && jr.FailureReason != 0)
            sb.AppendLine($"    FailureReason            {jr.FailureReason}");

        if ((mask & JoiningResultDataTypeFields.Trace) != 0 && jr.Trace is not null)
            FormatTrace(sb, jr.Trace);
    }

    private static void FormatResultValue(StringBuilder sb, ResultValueDataType rv, int indent)
    {
        var pad = new string(' ', indent);
        var units = NormalizeUnits(rv.EngineeringUnits?.DisplayName?.Text, rv.PhysicalQuantity);
        sb.AppendLine(
            $"{pad}{rv.Name ?? rv.ValueId ?? "?",-24} {rv.MeasuredValue,10:F3}  {units,-10} [{rv.ResultEvaluation}]");
    }

    private static void FormatTrace(StringBuilder sb, JoiningTraceDataType trace)
    {
        sb.AppendLine("    Trace");
        AppendField(sb, "TraceId", trace.TraceId, 6);
        AppendField(sb, "ResultId", trace.ResultId, 6);

        if (trace.StepTraces is null || trace.StepTraces.Count == 0)
        {
            sb.AppendLine("      StepTraces               (none)");
            return;
        }

        sb.AppendLine($"      StepTraces               ({trace.StepTraces.Count})");
        foreach (var stepTrace in trace.StepTraces)
        {
            sb.AppendLine($"        StepTraceId            {stepTrace.StepTraceId}");
            AppendField(sb, "StepResultId", stepTrace.StepResultId, 10);
            AppendField(sb, "NumberOfTracePoints", stepTrace.NumberOfTracePoints.ToString(CultureInfo.InvariantCulture), 10);
            AppendField(sb, "SamplingInterval", stepTrace.SamplingInterval.ToString(CultureInfo.InvariantCulture), 10);
            AppendField(sb, "StartTimeOffset", stepTrace.StartTimeOffset.ToString(CultureInfo.InvariantCulture), 10);

            var channels = stepTrace.StepTraceContent;
            if (channels is null || channels.Count == 0)
            {
                sb.AppendLine("          Channels              (none)");
                continue;
            }

            sb.AppendLine($"          Channels              ({channels.Count})");
            for (int i = 0; i < channels.Count; i++)
            {
                var channel = channels[i];
                var units = NormalizeUnits(channel.EngineeringUnits?.DisplayName?.Text, channel.PhysicalQuantity);
                sb.AppendLine($"            [{i}] {channel.Name ?? "Channel"}  SensorId={channel.SensorId ?? "-"}  PQ={channel.PhysicalQuantity}  Unit={units}");
                if (channel.Values is null || channel.Values.Count == 0)
                {
                    sb.AppendLine("              Values: (none)");
                    continue;
                }

                var values = string.Join(", ", channel.Values.Select(v => v.ToString("G6", CultureInfo.InvariantCulture)));
                sb.AppendLine($"              Values[{channel.Values.Count}]: {values}");
            }
        }
    }

    private static string NormalizeUnits(string? unitText, byte physicalQuantity)
    {
        if (string.IsNullOrWhiteSpace(unitText) || unitText == "?" || unitText == "�")
            return physicalQuantity == 3 ? "deg" : "";

        return unitText.Replace("°", "deg");
    }

    private static void AppendField(StringBuilder sb, string name, string? value, int indent = 2)
    {
        if (string.IsNullOrEmpty(value)) return;
        var pad = new string(' ', indent);
        sb.AppendLine($"{pad}{name,-28} {value}");
    }
}
