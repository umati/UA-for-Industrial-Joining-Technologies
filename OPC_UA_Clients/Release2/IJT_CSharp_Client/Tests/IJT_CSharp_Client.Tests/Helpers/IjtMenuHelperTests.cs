#nullable enable

using IJT_CSharp_Client.Helpers;
using Xunit;

namespace IJT_CSharp_Client.Tests.Helpers;

public class IjtMenuHelperTests
{
    [Fact]
    public async Task PrintUsage_MinimalArgs_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            IjtMenuHelper.PrintUsage(
                title: "GetJointListAsync",
                description: "Retrieves all joints.",
                inputs: ["ProductInstanceUri"],
                outputs: ["JointList", "Status"]));

        Assert.Null(ex);
    }

    [Fact]
    public async Task PrintUsage_WithTip_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            IjtMenuHelper.PrintUsage(
                title: "GetLatestResultAsync",
                description: "Returns the most recent result.",
                inputs: ["TimeoutMs"],
                outputs: ["Result", "Status"],
                tip: "Full payload is written to logs/result/result.json"));

        Assert.Null(ex);
    }

    [Fact]
    public async Task PrintUsage_EmptyInputsAndOutputs_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            IjtMenuHelper.PrintUsage(
                title: "NoArgs",
                description: "No inputs or outputs.",
                inputs: [],
                outputs: []));

        Assert.Null(ex);
    }

    [Fact]
    public async Task PrintUsage_LongTitle_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            IjtMenuHelper.PrintUsage(
                title: new string('A', 120),
                description: "Wide title that exceeds 64 chars — tests width calculation.",
                inputs: ["Input1"],
                outputs: ["Output1"]));

        Assert.Null(ex);
    }
}
