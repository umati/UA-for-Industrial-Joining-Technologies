using IJT_CSharp_Client.Helpers;
using Xunit;

namespace IJT_CSharp_Client.Tests.Helpers;

public class IjtFileLoggerTests
{
    [Fact]
    public void WriteResult_CreatesFile()
    {
        IjtFileLogger.WriteResult("test result content");
        Assert.True(File.Exists(IjtFileLogger.ResultLogPath));
    }

    [Fact]
    public void WriteResult_OverwritesPreviousContent()
    {
        IjtFileLogger.WriteResult("first");
        IjtFileLogger.WriteResult("second");

        var content = File.ReadAllText(IjtFileLogger.ResultLogPath);
        Assert.Contains("second", content);
        Assert.DoesNotContain("first", content);
    }

    [Fact]
    public void WriteEvent_CreatesFile()
    {
        IjtFileLogger.WriteEvent("test event content");
        Assert.True(File.Exists(IjtFileLogger.EventLogPath));
    }

    [Fact]
    public void WriteEvent_OverwritesPreviousContent()
    {
        IjtFileLogger.WriteEvent("event-one");
        IjtFileLogger.WriteEvent("event-two");

        var content = File.ReadAllText(IjtFileLogger.EventLogPath);
        Assert.Contains("event-two", content);
        Assert.DoesNotContain("event-one", content);
    }

    [Fact]
    public void LogPaths_AreUnderLogsDirectory()
    {
        Assert.Contains("logs", IjtFileLogger.ResultLogPath);
        Assert.Contains("logs", IjtFileLogger.EventLogPath);
        Assert.Contains(Path.Combine("logs", "result"), IjtFileLogger.ResultLogPath);
        Assert.Contains(Path.Combine("logs", "events"), IjtFileLogger.EventLogPath);
    }

    // ── New domain-specific write methods ─────────────────────────────────────

    [Fact]
    public void WriteJoiningProcessList_CreatesFile()
    {
        IjtFileLogger.WriteJoiningProcessList("process-list-content");
        Assert.True(File.Exists(IjtFileLogger.JoiningProcessListLogPath));
        Assert.Equal("process-list-content", File.ReadAllText(IjtFileLogger.JoiningProcessListLogPath));
    }

    [Fact]
    public void WriteSelectedProgram_CreatesFile()
    {
        IjtFileLogger.WriteSelectedProgram("selected-program-content");
        Assert.True(File.Exists(IjtFileLogger.SelectedProgramLogPath));
        Assert.Equal("selected-program-content", File.ReadAllText(IjtFileLogger.SelectedProgramLogPath));
    }

    [Fact]
    public void WriteJointList_CreatesFile()
    {
        IjtFileLogger.WriteJointList("joint-list-content");
        Assert.True(File.Exists(IjtFileLogger.JointListLogPath));
        Assert.Equal("joint-list-content", File.ReadAllText(IjtFileLogger.JointListLogPath));
    }

    [Fact]
    public void WriteJoint_CreatesFile()
    {
        IjtFileLogger.WriteJoint("joint-content");
        Assert.True(File.Exists(IjtFileLogger.JointLogPath));
        Assert.Equal("joint-content", File.ReadAllText(IjtFileLogger.JointLogPath));
    }

    [Fact]
    public void WriteIdentifiers_CreatesFile()
    {
        IjtFileLogger.WriteIdentifiers("identifiers-content");
        Assert.True(File.Exists(IjtFileLogger.IdentifiersLogPath));
        Assert.Equal("identifiers-content", File.ReadAllText(IjtFileLogger.IdentifiersLogPath));
    }

    [Fact]
    public void NewLogPaths_AreUnderLogsDirectory()
    {
        Assert.Contains(Path.Combine("logs", "joining_process"), IjtFileLogger.JoiningProcessListLogPath);
        Assert.Contains(Path.Combine("logs", "joining_process"), IjtFileLogger.SelectedProgramLogPath);
        Assert.Contains(Path.Combine("logs", "joint"), IjtFileLogger.JointListLogPath);
        Assert.Contains(Path.Combine("logs", "joint"), IjtFileLogger.JointLogPath);
        Assert.Contains(Path.Combine("logs", "entity_list"), IjtFileLogger.IdentifiersLogPath);
    }

    [Fact]
    public void BaseLogDir_ContainsLogs()
    {
        Assert.EndsWith("logs", IjtFileLogger.BaseLogDir);
    }

    [Fact]
    public void Write_OverwritesPreviousContent()
    {
        IjtFileLogger.WriteJointList("old-content");
        IjtFileLogger.WriteJointList("new-content");

        var content = File.ReadAllText(IjtFileLogger.JointListLogPath);
        Assert.Equal("new-content", content);
        Assert.DoesNotContain("old-content", content);
    }

    // ── WriteIOSignals ────────────────────────────────────────────────────────

    [Fact]
    public void WriteIOSignals_CreatesFile()
    {
        IjtFileLogger.WriteIOSignals("io-signals-content");
        Assert.True(File.Exists(IjtFileLogger.IOSignalsLogPath));
        Assert.Equal("io-signals-content", File.ReadAllText(IjtFileLogger.IOSignalsLogPath));
    }

    [Fact]
    public void WriteIOSignals_OverwritesPreviousContent()
    {
        IjtFileLogger.WriteIOSignals("signals-v1");
        IjtFileLogger.WriteIOSignals("signals-v2");

        var content = File.ReadAllText(IjtFileLogger.IOSignalsLogPath);
        Assert.Equal("signals-v2", content);
        Assert.DoesNotContain("signals-v1", content);
    }

    [Fact]
    public void IOSignalsLogPath_IsUnderLogsDirectory()
    {
        Assert.Contains(Path.Combine("logs", "io_signals"), IjtFileLogger.IOSignalsLogPath);
    }

    // ── WriteAsset / SanitizeFileName ─────────────────────────────────────────

    [Fact]
    public void WriteAsset_WithCleanKey_CreatesFile()
    {
        IjtFileLogger.WriteAsset("Controllers_Tool1", "asset-content");

        var expectedPath = Path.Combine(IjtFileLogger.AssetLogDir, "Controllers_Tool1.json");
        Assert.True(File.Exists(expectedPath));
        Assert.Equal("asset-content", File.ReadAllText(expectedPath));
    }

    [Fact]
    public void WriteAsset_WithInvalidChars_SanitizesFileName()
    {
        // OPC UA DisplayNames can contain '/', ':', '*', '?' — all invalid on Windows
        IjtFileLogger.WriteAsset("Controllers/Tool:A*B?C", "sanitized-content");

        // All invalid chars replaced with '_'
        var expectedPath = Path.Combine(IjtFileLogger.AssetLogDir, "Controllers_Tool_A_B_C.json");
        Assert.True(File.Exists(expectedPath), $"Expected file: {expectedPath}");
        Assert.Equal("sanitized-content", File.ReadAllText(expectedPath));
    }

    [Fact]
    public void WriteAsset_OverwritesPreviousContent()
    {
        IjtFileLogger.WriteAsset("Tools_Wrench1", "snapshot-1");
        IjtFileLogger.WriteAsset("Tools_Wrench1", "snapshot-2");

        var path = Path.Combine(IjtFileLogger.AssetLogDir, "Tools_Wrench1.json");
        Assert.Equal("snapshot-2", File.ReadAllText(path));
    }

    [Fact]
    public void AssetLogDir_IsUnderLogsDirectory()
    {
        Assert.Contains(Path.Combine("logs", "assets"), IjtFileLogger.AssetLogDir);
    }
}
