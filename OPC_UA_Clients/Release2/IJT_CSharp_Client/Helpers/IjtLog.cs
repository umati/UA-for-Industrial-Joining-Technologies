#nullable enable

using System.Collections.Concurrent;
using Microsoft.Extensions.Logging;

namespace IJT_CSharp_Client.Helpers;

/// <summary>
/// Application-wide logger factory for the IJT C# Client.
/// All classes obtain their typed <see cref="ILogger{T}"/> from here.
/// Configure verbosity via the <c>IJT_LOG_LEVEL</c> environment variable
/// (Trace / Debug / Information / Warning / Error / Critical).
/// </summary>
public static class IjtLog
{
    /// <summary>
    /// Shared console lock — use this in prompt writes so they don't interleave with log output.
    /// </summary>
    public static readonly object ConsoleLock = new();

    private static readonly object FactoryLock = new();
    private static ILoggerFactory _factory = CreateFactory();

    private static ILoggerFactory CreateFactory() => LoggerFactory.Create(builder =>
    {
        var levelStr = Environment.GetEnvironmentVariable("IJT_LOG_LEVEL") ?? "Information";
        var level = Enum.TryParse<LogLevel>(levelStr, ignoreCase: true, out var parsed)
            ? parsed
            : LogLevel.Information;

        builder
            .ClearProviders()
            .SetMinimumLevel(level)
            .AddProvider(new SynchronousConsoleLoggerProvider(level));
    });

    /// <summary>Creates a typed logger for <typeparamref name="T"/>.</summary>
    public static ILogger<T> For<T>()
    {
        lock (FactoryLock)
        {
            return _factory.CreateLogger<T>();
        }
    }

    /// <summary>Creates a named logger for a free-form category string.</summary>
    public static ILogger ForCategory(string category)
    {
        lock (FactoryLock)
        {
            return _factory.CreateLogger(category);
        }
    }

    /// <summary>Flushes and disposes the logger factory. Call once on application exit.</summary>
    public static void Shutdown()
    {
        lock (FactoryLock)
        {
            _factory.Dispose();
            _factory = CreateFactory();
        }
    }

    private sealed class SynchronousConsoleLoggerProvider(LogLevel minLevel) : ILoggerProvider
    {
        private readonly ConcurrentDictionary<string, SynchronousConsoleLogger> _loggers = new(StringComparer.Ordinal);

        public ILogger CreateLogger(string categoryName) =>
            _loggers.GetOrAdd(categoryName, static (name, state) => new SynchronousConsoleLogger(name, state), minLevel);

        public void Dispose() => _loggers.Clear();
    }

    private sealed class SynchronousConsoleLogger(string categoryName, LogLevel minLevel) : ILogger
    {
        private static readonly object ConsoleWriteLock = IjtLog.ConsoleLock;
        private readonly string _category = ShortCategory(categoryName);

        public IDisposable BeginScope<TState>(TState state) where TState : notnull => NoopScope.Instance;

        public bool IsEnabled(LogLevel logLevel) => logLevel >= minLevel && logLevel != LogLevel.None;

        public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception? exception,
            Func<TState, Exception?, string> formatter)
        {
            if (!IsEnabled(logLevel))
            {
                return;
            }

            var message = formatter(state, exception);
            if (string.IsNullOrWhiteSpace(message) && exception is null)
            {
                return;
            }

            var timestamp = DateTime.Now.ToString("HH:mm:ss.fff", System.Globalization.CultureInfo.InvariantCulture);
            var level = LevelTag(logLevel);
            var line = $"{timestamp} {level} [{_category}] {message}";

            lock (ConsoleWriteLock)
            {
                EnsureNewLineBoundary();
                WriteWithColor(line, logLevel);

                if (exception is not null)
                {
                    Console.WriteLine(exception);
                }
            }
        }

        private static void EnsureNewLineBoundary()
        {
            try
            {
                if (!Console.IsOutputRedirected && Console.CursorLeft > 0)
                {
                    Console.WriteLine();
                }
            }
            catch
            {
                // Non-interactive hosts may not support cursor APIs. Ignore and continue.
            }
        }

        private static void WriteWithColor(string line, LogLevel logLevel)
        {
            if (Console.IsOutputRedirected)
            {
                Console.WriteLine(line);
                return;
            }

            var color = ColorFor(logLevel);
            if (color is null)
            {
                Console.WriteLine(line);
                return;
            }

            var original = Console.ForegroundColor;
            Console.ForegroundColor = color.Value;
            Console.WriteLine(line);
            Console.ForegroundColor = original;
        }

        private static ConsoleColor? ColorFor(LogLevel level) => level switch
        {
            LogLevel.Warning => ConsoleColor.Yellow,
            LogLevel.Error => ConsoleColor.Red,
            LogLevel.Critical => ConsoleColor.Red,
            _ => null
        };

        private static string LevelTag(LogLevel level) => level switch
        {
            LogLevel.Trace => "TRACE",
            LogLevel.Debug => "DEBUG",
            LogLevel.Information => "INFO",
            LogLevel.Warning => "WARN",
            LogLevel.Error => "ERROR",
            LogLevel.Critical => "CRITICAL",
            _ => "LOG"
        };

        private static string ShortCategory(string category)
        {
            if (string.IsNullOrWhiteSpace(category))
            {
                return "App";
            }

            var i = category.LastIndexOf('.');
            return i >= 0 && i < category.Length - 1 ? category[(i + 1)..] : category;
        }

        private sealed class NoopScope : IDisposable
        {
            public static readonly NoopScope Instance = new();
            public void Dispose() { }
        }
    }
}
