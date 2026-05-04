#nullable enable

using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;
using Xunit;

namespace IJT_CSharp_Client.Tests.Helpers;

/// <summary>
/// Unit tests for <see cref="IjtLog"/> — exercises the public factory surface and
/// the private <c>SynchronousConsoleLogger</c> via the logger it returns.
/// </summary>
public sealed class IjtLogTests
{
    private static Type ConsoleLoggerType =>
        typeof(IjtLog).GetNestedType("SynchronousConsoleLogger", System.Reflection.BindingFlags.NonPublic)!;

    private static T InvokeConsoleLoggerHelper<T>(string methodName, params object[] args)
    {
        var method = ConsoleLoggerType.GetMethod(
            methodName,
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
        return (T)method!.Invoke(null, args)!;
    }

    // ── IjtLog.For<T> ─────────────────────────────────────────────────────────

    [Fact]
    public void For_ReturnsNonNullLogger()
    {
        var logger = IjtLog.For<IjtLogTests>();
        Assert.NotNull(logger);
    }

    [Fact]
    public void For_ReturnsSameLoggerForSameType()
    {
        var a = IjtLog.For<IjtLogTests>();
        var b = IjtLog.For<IjtLogTests>();
        Assert.NotNull(a);
        Assert.NotNull(b);
    }

    // ── IjtLog.ForCategory ────────────────────────────────────────────────────

    [Fact]
    public void ForCategory_WithDottedName_ReturnsNonNullLogger()
    {
        var logger = IjtLog.ForCategory("Some.Dotted.Category");
        Assert.NotNull(logger);
    }

    [Fact]
    public void ForCategory_WithSimpleName_ReturnsNonNullLogger()
    {
        var logger = IjtLog.ForCategory("MyApp");
        Assert.NotNull(logger);
    }

    // ── ConsoleLock ───────────────────────────────────────────────────────────

    [Fact]
    public void ConsoleLock_IsNotNull()
    {
        Assert.NotNull(IjtLog.ConsoleLock);
    }

    // ── SynchronousConsoleLogger — via ILogger surface ────────────────────────

    [Fact]
    public void Logger_IsEnabled_InformationLevel_ReturnsTrue()
    {
        var logger = IjtLog.For<IjtLogTests>();
        // Default level is Information (from env or fallback)
        Assert.True(logger.IsEnabled(LogLevel.Information));
    }

    [Fact]
    public void Logger_IsEnabled_NoneLevel_ReturnsFalse()
    {
        var logger = IjtLog.For<IjtLogTests>();
        Assert.False(logger.IsEnabled(LogLevel.None));
    }

    [Fact]
    public void Logger_BeginScope_ReturnsNonNullDisposable()
    {
        var logger = IjtLog.For<IjtLogTests>();
        using var scope = logger.BeginScope("test-scope");
        Assert.NotNull(scope);
    }

    [Fact]
    public void Logger_LogInformation_DoesNotThrow()
    {
        var logger = IjtLog.For<IjtLogTests>();
        var ex = Record.Exception(() => logger.LogInformation("Unit test log message"));
        Assert.Null(ex);
    }

    [Fact]
    public void Logger_LogWarning_DoesNotThrow()
    {
        var logger = IjtLog.For<IjtLogTests>();
        var ex = Record.Exception(() => logger.LogWarning("Unit test warning message"));
        Assert.Null(ex);
    }

    [Fact]
    public void Logger_LogError_DoesNotThrow()
    {
        var logger = IjtLog.For<IjtLogTests>();
        var ex = Record.Exception(() => logger.LogError("Unit test error message"));
        Assert.Null(ex);
    }

    [Fact]
    public void Logger_LogCritical_DoesNotThrow()
    {
        var logger = IjtLog.For<IjtLogTests>();
        var ex = Record.Exception(() => logger.LogCritical("Unit test critical message"));
        Assert.Null(ex);
    }

    [Fact]
    public void Logger_LogDebug_DoesNotThrow()
    {
        var logger = IjtLog.For<IjtLogTests>();
        var ex = Record.Exception(() => logger.LogDebug("Unit test debug message"));
        Assert.Null(ex);
    }

    [Fact]
    public void Logger_LogTrace_DoesNotThrow()
    {
        var logger = IjtLog.For<IjtLogTests>();
        var ex = Record.Exception(() => logger.LogTrace("Unit test trace message"));
        Assert.Null(ex);
    }

    [Fact]
    public void Logger_LogWithException_DoesNotThrow()
    {
        var logger = IjtLog.For<IjtLogTests>();
        var ex = Record.Exception(() =>
            logger.LogError(new InvalidOperationException("inner"), "Error with exception"));
        Assert.Null(ex);
    }

    [Fact]
    public void Logger_LogEmptyMessage_DoesNotThrow()
    {
        var logger = IjtLog.For<IjtLogTests>();
        // Empty message with no exception should be silently skipped
        var ex = Record.Exception(() => logger.LogInformation(""));
        Assert.Null(ex);
    }

    [Fact]
    public void Logger_LogWithWhitespaceMessage_DoesNotThrow()
    {
        var logger = IjtLog.For<IjtLogTests>();
        var ex = Record.Exception(() => logger.LogInformation("   "));
        Assert.Null(ex);
    }

    [Fact]
    public void ForCategory_DottedName_LogsWithoutThrow()
    {
        var logger = IjtLog.ForCategory("IJT_CSharp_Client.Client.JoiningSystem");
        var ex = Record.Exception(() => logger.LogInformation("Category-based log entry"));
        Assert.Null(ex);
    }

    [Fact]
    public void ForCategory_SingleSegmentName_LogsWithoutThrow()
    {
        var logger = IjtLog.ForCategory("JoiningSystem");
        var ex = Record.Exception(() => logger.LogWarning("Single segment category log"));
        Assert.Null(ex);
    }

    // ── SynchronousConsoleLogger private formatting helpers ──────────────────

    [Theory]
    [InlineData(LogLevel.Trace, "TRACE")]
    [InlineData(LogLevel.Debug, "DEBUG")]
    [InlineData(LogLevel.Information, "INFO")]
    [InlineData(LogLevel.Warning, "WARN")]
    [InlineData(LogLevel.Error, "ERROR")]
    [InlineData(LogLevel.Critical, "CRITICAL")]
    [InlineData(LogLevel.None, "LOG")]
    public void LevelTag_ReturnsExpectedTag(LogLevel level, string expected)
    {
        Assert.Equal(expected, InvokeConsoleLoggerHelper<string>("LevelTag", level));
    }

    [Theory]
    [InlineData(LogLevel.Warning, ConsoleColor.Yellow)]
    [InlineData(LogLevel.Error, ConsoleColor.Red)]
    [InlineData(LogLevel.Critical, ConsoleColor.Red)]
    public void ColorFor_ReturnsColorForWarningAndErrors(LogLevel level, ConsoleColor expected)
    {
        Assert.Equal(expected, InvokeConsoleLoggerHelper<ConsoleColor?>("ColorFor", level));
    }

    [Fact]
    public void ColorFor_ReturnsNullForInformation()
    {
        Assert.Null(InvokeConsoleLoggerHelper<ConsoleColor?>("ColorFor", LogLevel.Information));
    }

    [Theory]
    [InlineData("", "App")]
    [InlineData("IJT_CSharp_Client.Client.JoiningSystem", "JoiningSystem")]
    [InlineData("JoiningSystem", "JoiningSystem")]
    public void ShortCategory_ReturnsReadableCategory(string category, string expected)
    {
        Assert.Equal(expected, InvokeConsoleLoggerHelper<string>("ShortCategory", category));
    }
}
