using IJT_CSharp_Client.Helpers;
using Xunit;

namespace IJT_CSharp_Client.Tests.Helpers;

public class IjtFileLoggerTests : IDisposable
{
    private readonly string _tempRoot;
    private readonly IDisposable _overrideScope;

    public IjtFileLoggerTests()
    {
        _tempRoot = Path.Combine(Path.GetTempPath(), "ijt-file-logger-tests", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_tempRoot);
        _overrideScope = IjtFileLogger.PushBaseLogDirOverride(Path.Combine(_tempRoot, "logs"));
    }

    public void Dispose()
    {
        _overrideScope.Dispose();
        if (Directory.Exists(_tempRoot))
        {
            try
            {
                Directory.Delete(_tempRoot, recursive: true);
            }
            catch (IOException)
            {
            }
            catch (UnauthorizedAccessException)
            {
            }
        }
    }

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

    // ── WriteResultTimestamped ───────────────────────────────────────────────

    [Fact]
    public void WriteResultTimestamped_CreatesTimestampedFile()
    {
        var path = IjtFileLogger.WriteResultTimestamped("timestamped-content", "RES-001", "TestResult");

        Assert.True(File.Exists(path));
        Assert.Equal("timestamped-content", File.ReadAllText(path));
        Assert.Contains("TestResult", Path.GetFileName(path));
        Assert.Contains("RES-001", Path.GetFileName(path));
        Assert.EndsWith(".json", path);
    }

    [Fact]
    public void WriteResultTimestamped_AlsoUpdatesLatestResultJson()
    {
        IjtFileLogger.WriteResultTimestamped("latest-via-timestamped", "RES-002");

        Assert.True(File.Exists(IjtFileLogger.ResultLogPath));
        Assert.Equal("latest-via-timestamped", File.ReadAllText(IjtFileLogger.ResultLogPath));
    }

    [Fact]
    public void WriteResultTimestamped_MultipleCallsCreateSeparateFiles()
    {
        var path1 = IjtFileLogger.WriteResultTimestamped("result-one", "R1", "First");
        // Small delay to ensure different timestamps
        System.Threading.Thread.Sleep(5);
        var path2 = IjtFileLogger.WriteResultTimestamped("result-two", "R2", "Second");

        Assert.NotEqual(path1, path2);
        Assert.True(File.Exists(path1));
        Assert.True(File.Exists(path2));
        Assert.Equal("result-one", File.ReadAllText(path1));
        Assert.Equal("result-two", File.ReadAllText(path2));
    }

    [Fact]
    public void WriteResultTimestamped_WithNullIdAndName_CreatesFileWithTimestampOnly()
    {
        var path = IjtFileLogger.WriteResultTimestamped("content-only");

        Assert.True(File.Exists(path));
        Assert.EndsWith(".json", path);
    }

    [Fact]
    public void ResultsLogDir_IsUnderLogsDirectory()
    {
        Assert.Contains(Path.Combine("logs", "results"), IjtFileLogger.ResultsLogDir);
    }

    // ── WriteEventTimestamped ────────────────────────────────────────────────

    [Fact]
    public void WriteEventTimestamped_CreatesTimestampedFile()
    {
        var path = IjtFileLogger.WriteEventTimestamped("event-content", "1001", "Tool connected");

        Assert.True(File.Exists(path));
        Assert.Equal("event-content", File.ReadAllText(path));
        Assert.Contains("1001", Path.GetFileName(path));
        Assert.Contains("Tool connected", Path.GetFileName(path));
        Assert.EndsWith(".json", path);
    }

    [Fact]
    public void WriteEventTimestamped_AlsoUpdatesLatestEventJson()
    {
        IjtFileLogger.WriteEventTimestamped("latest-event", "2001");

        Assert.True(File.Exists(IjtFileLogger.EventLogPath));
        Assert.Equal("latest-event", File.ReadAllText(IjtFileLogger.EventLogPath));
    }

    [Fact]
    public void WriteEventTimestamped_MultipleCallsCreateSeparateFiles()
    {
        var path1 = IjtFileLogger.WriteEventTimestamped("evt-one", "E1");
        System.Threading.Thread.Sleep(5);
        var path2 = IjtFileLogger.WriteEventTimestamped("evt-two", "E2");

        Assert.NotEqual(path1, path2);
        Assert.True(File.Exists(path1));
        Assert.True(File.Exists(path2));
    }

    [Fact]
    public void EventsHistoryLogDir_IsUnderLogsDirectory()
    {
        Assert.Contains(Path.Combine("logs", "events_history"), IjtFileLogger.EventsHistoryLogDir);
    }

    // ── ClearSessionLogs ─────────────────────────────────────────────────────

    [Fact]
    public void ClearSessionLogs_RemovesTimestampedDirs()
    {
        // Create some timestamped files first
        IjtFileLogger.WriteResultTimestamped("r1", "R1");
        IjtFileLogger.WriteEventTimestamped("e1", "E1");

        Assert.True(Directory.Exists(IjtFileLogger.ResultsLogDir));
        Assert.True(Directory.Exists(IjtFileLogger.EventsHistoryLogDir));

        IjtFileLogger.ClearSessionLogs();

        Assert.False(Directory.Exists(IjtFileLogger.ResultsLogDir));
        Assert.False(Directory.Exists(IjtFileLogger.EventsHistoryLogDir));
    }

    [Fact]
    public void ClearSessionLogs_DoesNotRemoveLatestSnapshots()
    {
        IjtFileLogger.WriteResult("latest-result");
        IjtFileLogger.WriteEvent("latest-event");

        IjtFileLogger.ClearSessionLogs();

        // Latest snapshot files should still exist
        Assert.True(File.Exists(IjtFileLogger.ResultLogPath));
        Assert.True(File.Exists(IjtFileLogger.EventLogPath));
    }

    [Fact]
    public void ClearSessionLogs_DoesNotThrow_WhenDirsDoNotExist()
    {
        // Should be safe to call even when directories don't exist yet
        var ex = Record.Exception(() => IjtFileLogger.ClearSessionLogs());
        Assert.Null(ex);
    }
}
