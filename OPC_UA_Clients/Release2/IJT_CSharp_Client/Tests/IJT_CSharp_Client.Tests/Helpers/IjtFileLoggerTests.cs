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
        Assert.Equal("second", content);
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
        Assert.Equal("event-two", content);
    }

    [Fact]
    public void LogPaths_AreUnderLogsDirectory()
    {
        Assert.Contains("logs", IjtFileLogger.ResultLogPath);
        Assert.Contains("logs", IjtFileLogger.EventLogPath);
        Assert.Contains("results", IjtFileLogger.ResultLogPath);
        Assert.Contains("events", IjtFileLogger.EventLogPath);
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
        Assert.Contains(Path.Combine("logs", "joints"), IjtFileLogger.JointListLogPath);
        Assert.Contains(Path.Combine("logs", "joints"), IjtFileLogger.JointLogPath);
        Assert.Contains(Path.Combine("logs", "identifiers"), IjtFileLogger.IdentifiersLogPath);
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
}
