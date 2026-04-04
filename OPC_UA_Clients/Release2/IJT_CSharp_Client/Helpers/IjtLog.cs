#nullable enable

using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Console;

namespace IJT_CSharp_Client.Helpers;

/// <summary>
/// Application-wide logger factory for the IJT C# Client.
/// All classes obtain their typed <see cref="ILogger{T}"/> from here.
/// Configure verbosity via the <c>IJT_LOG_LEVEL</c> environment variable
/// (Trace / Debug / Information / Warning / Error / Critical).
/// </summary>
public static class IjtLog
{
    private static readonly ILoggerFactory _factory = LoggerFactory.Create(builder =>
    {
        var levelStr = Environment.GetEnvironmentVariable("IJT_LOG_LEVEL") ?? "Information";
        var level    = Enum.TryParse<LogLevel>(levelStr, ignoreCase: true, out var l)
                       ? l : LogLevel.Information;

        builder
            .SetMinimumLevel(level)
            .AddSimpleConsole(o =>
            {
                o.TimestampFormat = "HH:mm:ss.fff ";
                o.SingleLine      = false;
                o.ColorBehavior   = LoggerColorBehavior.Enabled;
                o.UseUtcTimestamp = false;
            });
    });

    /// <summary>Creates a typed logger for <typeparamref name="T"/>.</summary>
    public static ILogger<T> For<T>() => _factory.CreateLogger<T>();

    /// <summary>Creates a named logger for a free-form category string.</summary>
    public static ILogger ForCategory(string category) => _factory.CreateLogger(category);

    /// <summary>Flushes and disposes the logger factory. Call once on application exit.</summary>
    public static void Shutdown() => _factory.Dispose();
}
