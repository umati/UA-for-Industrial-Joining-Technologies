#nullable enable

using System.Text;
using Microsoft.Extensions.Logging;

namespace IJT_CSharp_Client.Helpers;

/// <summary>
/// Writes method output payloads to domain-specific log files for offline inspection.
/// Each call OVERWRITES the file — only the most recent payload per domain is kept.
///
/// File layout (relative to executable):
///   logs/
///     results/result.log                    — last ResultDataType (method call or event)
///     events/event.log                      — last JoiningSystemEvent received
///     joining_process/process_list.log      — last GetJoiningProcessList output
///     joining_process/selected_program.log  — last GetSelectedJoiningProgram output
///     joints/joint_list.log                 — last GetJointList output
///     joints/joint.log                      — last GetJoint output
///     identifiers/identifiers.log           — last GetIdentifiers output
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

    private static readonly string _joiningProcessListLogPath =
        Path.Combine(_baseDir, "joining_process", "process_list.log");

    private static readonly string _selectedProgramLogPath =
        Path.Combine(_baseDir, "joining_process", "selected_program.log");

    private static readonly string _jointListLogPath =
        Path.Combine(_baseDir, "joints", "joint_list.log");

    private static readonly string _jointLogPath =
        Path.Combine(_baseDir, "joints", "joint.log");

    private static readonly string _identifiersLogPath =
        Path.Combine(_baseDir, "identifiers", "identifiers.log");

    /// <summary>Overwrites result.log with the given text content.</summary>
    public static void WriteResult(string content) => WriteFile(_resultLogPath, content);

    /// <summary>Overwrites event.log with the given text content.</summary>
    public static void WriteEvent(string content) => WriteFile(_eventLogPath, content);

    /// <summary>Overwrites joining_process/process_list.log with the given text content.</summary>
    public static void WriteJoiningProcessList(string content) => WriteFile(_joiningProcessListLogPath, content);

    /// <summary>Overwrites joining_process/selected_program.log with the given text content.</summary>
    public static void WriteSelectedProgram(string content) => WriteFile(_selectedProgramLogPath, content);

    /// <summary>Overwrites joints/joint_list.log with the given text content.</summary>
    public static void WriteJointList(string content) => WriteFile(_jointListLogPath, content);

    /// <summary>Overwrites joints/joint.log with the given text content.</summary>
    public static void WriteJoint(string content) => WriteFile(_jointLogPath, content);

    /// <summary>Overwrites identifiers/identifiers.log with the given text content.</summary>
    public static void WriteIdentifiers(string content) => WriteFile(_identifiersLogPath, content);

    /// <summary>Base log directory (relative to executable).</summary>
    public static string BaseLogDir => _baseDir;

    public static string ResultLogPath => _resultLogPath;
    public static string EventLogPath => _eventLogPath;
    public static string JoiningProcessListLogPath => _joiningProcessListLogPath;
    public static string SelectedProgramLogPath => _selectedProgramLogPath;
    public static string JointListLogPath => _jointListLogPath;
    public static string JointLogPath => _jointLogPath;
    public static string IdentifiersLogPath => _identifiersLogPath;

    // Single lock for all file writes. Event-handler callbacks (subscription thread) and
    // menu calls (main thread) can race on the same file (e.g. result.log), so all writes
    // must be serialised.
    private static readonly Lock _fileLock = new();

    private static void WriteFile(string path, string content)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            lock (_fileLock)
            {
                File.WriteAllText(path, content, Encoding.UTF8);
            }
        }
        catch (IOException ex) { _log.LogWarning("Write failed: {Message}", ex.Message); }
        catch (UnauthorizedAccessException ex) { _log.LogWarning("Access denied: {Message}", ex.Message); }
    }
}
