#nullable enable

namespace IJT_CSharp_Client.Helpers;

/// <summary>
/// EntityType values defined in the IJT Base specification (OPC 40450-1, Table 211).
/// Source: common_system_data_t.h (server) and entity-data-type.mjs (web client).
/// Values are Int16 - 0 to 41 are spec-defined; negative values are vendor-specific.
/// </summary>
public static class IjtEntityTypes
{
    /// <summary>Full lookup: numeric value -> name string.</summary>
    public static readonly IReadOnlyDictionary<short, string> Names =
        new Dictionary<short, string>
        {
            [0] = "UNDEFINED",
            [1] = "OTHER",
            [2] = "ASSET",
            [3] = "CONTROLLER",
            [4] = "TOOL",
            [5] = "SERVO",
            [6] = "MEMORY_DEVICE",
            [7] = "SENSOR",
            [8] = "CABLE",
            [9] = "BATTERY",
            [10] = "POWER_SUPPLY",
            [11] = "FEEDER",
            [12] = "ACCESSORY",
            [13] = "SUB_COMPONENT",
            [14] = "SOFTWARE",
            [15] = "RESULT",
            [16] = "EVENT",
            [17] = "ERROR_TYPE",
            [18] = "SYSTEM_TYPE",
            [19] = "LOG",
            [20] = "VEHICLE",
            [21] = "PRODUCT",
            [22] = "PART",
            [23] = "JOINT",
            [24] = "MODEL",
            [25] = "ORDER",
            [26] = "JOINING_PROCESS",
            [27] = "PROGRAM",
            [28] = "JOB",
            [29] = "BATCH",
            [30] = "RECIPE",
            [31] = "TASK",
            [32] = "PROCESS_TYPE",
            [33] = "CONFIGURATION",
            [34] = "SOCKET_TYPE",
            [35] = "CHANNEL",
            [36] = "STATION",
            [37] = "PRODUCTION_LINE",
            [38] = "LOCATION",
            [39] = "USER_TYPE",
            [40] = "PARENT_TYPE",
            [41] = "VIRTUAL_STATION",
        };

    /// <summary>Returns the name for a given EntityType value, or the numeric string if unknown.</summary>
    public static string Resolve(short value) =>
        Names.TryGetValue(value, out var name) ? name : $"VENDOR_SPECIFIC({value})";

    /// <summary>
    /// Prints all EntityType values to the console in a 3-column table.
    /// </summary>
    public static void PrintTable()
    {
        Console.WriteLine("  EntityType values:");
        var entries = Names.OrderBy(kv => kv.Key).ToList();
        int cols = 3;
        int rows = (int)Math.Ceiling(entries.Count / (double)cols);
        for (int r = 0; r < rows; r++)
        {
            Console.Write("  ");
            for (int c = 0; c < cols; c++)
            {
                int idx = r + c * rows;
                if (idx < entries.Count)
                {
                    var kv = entries[idx];
                    Console.Write($"  {kv.Key,3} = {kv.Value,-20}");
                }
            }
            Console.WriteLine();
        }
        Console.WriteLine("  (negative values = vendor-specific)");
    }
}
