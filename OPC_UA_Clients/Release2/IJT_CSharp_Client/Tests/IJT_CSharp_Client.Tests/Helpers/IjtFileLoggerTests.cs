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
}
