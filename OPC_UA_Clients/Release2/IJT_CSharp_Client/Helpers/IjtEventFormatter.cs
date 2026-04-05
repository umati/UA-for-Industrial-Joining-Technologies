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
                sb.AppendLine($"    EntityId={entity.EntityId}  Name={entity.Name}  Type={entity.EntityType}  External={entity.IsExternal}");
        }

        if (reportedValues?.Length > 0)
        {
            sb.AppendLine($"  {"ReportedValues",-28} ({reportedValues.Length} values)");
            foreach (var r in reportedValues)
                sb.AppendLine($"    {r.Name,-24} Value={r.CurrentValue}  Unit={r.EngineeringUnits?.DisplayName?.Text}  Low={r.LowLimit}  High={r.HighLimit}");
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
