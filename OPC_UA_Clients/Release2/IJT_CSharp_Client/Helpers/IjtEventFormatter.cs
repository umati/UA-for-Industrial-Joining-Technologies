#nullable enable

using System.Text;

namespace IJT_CSharp_Client.Helpers;

/// <summary>
/// Formats <b>JoiningSystemEvent</b> payloads as human-readable text.
/// <para>
/// JoiningSystemEvent is a general-purpose event fired by the joining system for operational
/// notifications — tool connected/disconnected, controller state changes, alarms, status updates, etc.
/// It is distinct from result events: it does NOT carry a ResultDataType payload.
/// </para>
/// Returns strings so callers can print to console, write to file, or both.
/// </summary>
public static class IjtEventFormatter
{
    /// <summary>
    /// Formats a JoiningSystemEvent into a readable multi-line string.
    /// Includes all five JoiningSystemEventContent fields:
    /// EventCode, EventText, JoiningTechnology, AssociatedEntities, ReportedValues.
    /// </summary>
    public static string FormatJoiningSystemEvent(
        string? eventCode,
        string? eventText,
        string? joiningTechnology,
        DateTime eventTime,
        UAModel.IJTBase.EntityDataType[]? associatedEntities = null,
        UAModel.IJTBase.ReportedValueDataType[]? reportedValues = null)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"Received: {eventTime:yyyy-MM-dd HH:mm:ss.fff} UTC");
        sb.AppendLine();
        sb.AppendLine("JOINING SYSTEM EVENT");
        AppendField(sb, "EventCode", eventCode);
        AppendField(sb, "EventText", eventText);
        AppendField(sb, "JoiningTechnology", joiningTechnology);

        if (associatedEntities?.Length > 0)
        {
            sb.AppendLine($"  {"AssociatedEntities",-28} ({associatedEntities.Length} entities)");
            foreach (var entity in associatedEntities)
                sb.AppendLine($"    [{IjtEntityTypes.Resolve(entity.EntityType),-20}] Id={entity.EntityId}  Name={entity.Name}  External={entity.IsExternal}");
        }

        if (reportedValues?.Length > 0)
        {
            sb.AppendLine($"  {"ReportedValues",-28} ({reportedValues.Length} values)");
            foreach (var r in reportedValues)
            {
                var val = r.CurrentValue.Value is double d ? d
                        : r.CurrentValue.Value is float f ? (double)f
                        : r.CurrentValue.Value is int i ? (double)i
                        : r.CurrentValue.Value is long l ? (double)l
                        : (double?)null;
                var valStr = val.HasValue ? $"{val.Value,10:F3}" : $"{r.CurrentValue.Value,10}";
                sb.AppendLine($"    {r.Name,-24} {valStr}  {r.EngineeringUnits?.DisplayName?.Text,-10}  Low={r.LowLimit}  High={r.HighLimit}");
            }
        }

        return sb.ToString();
    }

    // ── private helpers ───────────────────────────────────────────────────────

    private static void AppendField(StringBuilder sb, string name, string? value)
    {
        if (string.IsNullOrEmpty(value)) return;
        sb.AppendLine($"  {name,-28} {value}");
    }
}
