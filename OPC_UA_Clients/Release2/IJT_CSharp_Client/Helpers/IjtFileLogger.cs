#nullable enable

using System.Text;
using Microsoft.Extensions.Logging;

namespace IJT_CSharp_Client.Helpers;

/// <summary>
/// Writes the latest received result and event payloads to log files for offline inspection.
/// Each call OVERWRITES the file — only the most recently received payload is kept.
///
/// File layout (relative to executable):
///   logs/
///     results/result.log   — last ResultDataType received
///     events/event.log     — last JoiningSystemEvent received
/// </summary>
public static class IjtFileLogger
{
    private static readonly ILogger _log = IjtLog.ForCategory("IJT.FileLogger");

    private static readonly string _baseDir =
        Path.Combine(AppContext.BaseDirectory, "logs");

    private static readonly string _resultLogPath =
        Path.Combine(_baseDir, "results", "result.log");

    private static readonly string _eventLogPath =
        Path.Combine(_baseDir, "events", "event.log");

    /// <summary>Overwrites result.log with the given text content.</summary>
    public static void WriteResult(string content)
        => WriteFile(_resultLogPath, content);

    /// <summary>Overwrites event.log with the given text content.</summary>
    public static void WriteEvent(string content)
        => WriteFile(_eventLogPath, content);

    private static void WriteFile(string path, string content)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.WriteAllText(path, content, Encoding.UTF8);
        }
        catch (IOException ex) { _log.LogWarning("Write failed: {Message}", ex.Message); }
        catch (UnauthorizedAccessException ex) { _log.LogWarning("Access denied: {Message}", ex.Message); }
    }

    public static string ResultLogPath => _resultLogPath;
    public static string EventLogPath => _eventLogPath;
}
