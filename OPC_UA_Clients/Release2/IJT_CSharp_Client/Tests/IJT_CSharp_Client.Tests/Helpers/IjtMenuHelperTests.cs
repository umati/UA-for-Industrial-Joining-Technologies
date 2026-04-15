#nullable enable

using IJT_CSharp_Client.Helpers;
using Xunit;

namespace IJT_CSharp_Client.Tests.Helpers;

public class IjtMenuHelperTests
{
    [Fact]
    public void PrintUsage_MinimalArgs_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            IjtMenuHelper.PrintUsage(
                title: "GetJointList",
                description: "Retrieves all joints.",
                inputs: ["ProductInstanceUri"],
                outputs: ["JointList", "Status"]));

        Assert.Null(ex);
    }

    [Fact]
    public void PrintUsage_WithTip_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            IjtMenuHelper.PrintUsage(
                title: "GetLatestResult",
                description: "Returns the most recent result.",
                inputs: ["TimeoutMs"],
                outputs: ["Result", "Status"],
                tip: "Full payload is written to logs/results/result.log"));

        Assert.Null(ex);
    }

    [Fact]
    public void PrintUsage_EmptyInputsAndOutputs_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            IjtMenuHelper.PrintUsage(
                title: "NoArgs",
                description: "No inputs or outputs.",
                inputs: [],
                outputs: []));

        Assert.Null(ex);
    }

    [Fact]
    public void PrintUsage_LongTitle_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            IjtMenuHelper.PrintUsage(
                title: new string('A', 120),
                description: "Wide title that exceeds 64 chars — tests width calculation.",
                inputs: ["Input1"],
                outputs: ["Output1"]));

        Assert.Null(ex);
    }
}
