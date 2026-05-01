#nullable enable

using IJT_CSharp_Client.Helpers;
using Xunit;

namespace IJT_CSharp_Client.Tests.Helpers;

/// <summary>
/// Unit tests for <see cref="IjtEntityTypes"/> — authoritative EntityType lookup.
/// Source: OPC 40450-1 Section 10.10 / Table 226.
/// </summary>
public class IjtEntityTypesTests
{
    // ── Names dictionary ──────────────────────────────────────────────────────

    [Fact]
    public void Names_Contains43Entries()
    {
        Assert.Equal(43, IjtEntityTypes.Names.Count);
    }

    [Fact]
    public void Names_StartsAt0_EndsAt42()
    {
        Assert.True(IjtEntityTypes.Names.ContainsKey(0));
        Assert.True(IjtEntityTypes.Names.ContainsKey(42));
    }

    [Fact]
    public void Names_AllKeysAreContiguous_0Through42()
    {
        for (short i = 0; i <= 42; i++)
            Assert.True(IjtEntityTypes.Names.ContainsKey(i), $"Missing EntityType key: {i}");
    }

    [Fact]
    public void Names_NoNullOrEmptyValues()
    {
        foreach (var kv in IjtEntityTypes.Names)
            Assert.False(string.IsNullOrWhiteSpace(kv.Value),
                $"EntityType {kv.Key} has null/empty name");
    }

    // ── Spec-mandated values (OPC 40450-1 Section 10.10 / Table 226) ─────────

    [Theory]
    [InlineData(0, "UNDEFINED")]
    [InlineData(1, "OTHER")]
    [InlineData(2, "ASSET")]
    [InlineData(3, "CONTROLLER")]
    [InlineData(4, "TOOL")]
    [InlineData(5, "SERVO")]
    [InlineData(6, "MEMORY_DEVICE")]
    [InlineData(7, "SENSOR")]
    [InlineData(8, "CABLE")]
    [InlineData(9, "BATTERY")]
    [InlineData(10, "POWER_SUPPLY")]
    [InlineData(11, "FEEDER")]
    [InlineData(12, "ACCESSORY")]
    [InlineData(13, "SUB_COMPONENT")]
    [InlineData(14, "SOFTWARE")]
    [InlineData(15, "RESULT")]
    [InlineData(16, "EVENT")]
    [InlineData(17, "ERROR_TYPE")]
    [InlineData(18, "SYSTEM_TYPE")]
    [InlineData(19, "LOG")]
    [InlineData(20, "VEHICLE")]
    [InlineData(21, "PRODUCT")]
    [InlineData(22, "PART")]
    [InlineData(23, "JOINT")]
    [InlineData(24, "MODEL")]
    [InlineData(25, "ORDER")]
    [InlineData(26, "JOINING_PROCESS")]
    [InlineData(27, "PROGRAM")]
    [InlineData(28, "JOB")]
    [InlineData(29, "BATCH")]
    [InlineData(30, "RECIPE")]
    [InlineData(31, "TASK")]
    [InlineData(32, "PROCESS_TYPE")]
    [InlineData(33, "CONFIGURATION")]
    [InlineData(34, "SOCKET_TYPE")]
    [InlineData(35, "CHANNEL")]
    [InlineData(36, "STATION")]
    [InlineData(37, "PRODUCTION_LINE")]
    [InlineData(38, "LOCATION")]
    [InlineData(39, "USER_TYPE")]
    [InlineData(40, "PARENT_TYPE")]
    [InlineData(41, "VIRTUAL_STATION")]
    [InlineData(42, "JOINT_COMPONENT")]
    public void Names_SpecMandatedValue_IsCorrect(short value, string expectedName)
    {
        Assert.Equal(expectedName, IjtEntityTypes.Names[value]);
    }

    // ── Resolve ───────────────────────────────────────────────────────────────

    [Theory]
    [InlineData(0, "UNDEFINED")]
    [InlineData(1, "OTHER")]
    [InlineData(20, "VEHICLE")]
    [InlineData(41, "VIRTUAL_STATION")]
    [InlineData(42, "JOINT_COMPONENT")]
    public void Resolve_KnownValue_ReturnsExpectedName(short value, string expectedName)
    {
        Assert.Equal(expectedName, IjtEntityTypes.Resolve(value));
    }

    [Theory]
    [InlineData(-1)]
    [InlineData(100)]
    [InlineData(short.MaxValue)]
    [InlineData(short.MinValue)]
    public void Resolve_UnknownValue_ReturnsVendorSpecificString(short value)
    {
        var result = IjtEntityTypes.Resolve(value);
        Assert.StartsWith("VENDOR_SPECIFIC(", result);
        Assert.Contains(value.ToString(), result);
    }

    [Fact]
    public void Resolve_AllSpecValues_NeverReturnsVendorSpecific()
    {
        for (short i = 0; i <= 42; i++)
        {
            var result = IjtEntityTypes.Resolve(i);
            Assert.DoesNotContain("VENDOR_SPECIFIC", result);
        }
    }

    // ── PrintTable ────────────────────────────────────────────────────────────

    [Fact]
    public void PrintTable_DoesNotThrow()
    {
        // Redirect console output to avoid noise during test run
        var original = Console.Out;
        Console.SetOut(TextWriter.Null);
        try
        {
            var ex = Record.Exception(() => IjtEntityTypes.PrintTable());
            Assert.Null(ex);
        }
        finally
        {
            Console.SetOut(original);
        }
    }

    [Fact]
    public void PrintTable_OutputContainsAllSpecMandatedNames()
    {
        var sb = new System.Text.StringBuilder();
        var original = Console.Out;
        Console.SetOut(new System.IO.StringWriter(sb));
        try
        {
            IjtEntityTypes.PrintTable();
        }
        finally
        {
            Console.SetOut(original);
        }
        var output = sb.ToString();

        // Spot-check key names appear in output
        Assert.Contains("UNDEFINED", output);
        Assert.Contains("VEHICLE", output);
        Assert.Contains("VIRTUAL_STATION", output);
        Assert.Contains("JOINT_COMPONENT", output);
        Assert.Contains("JOINING_PROCESS", output);
    }
}
