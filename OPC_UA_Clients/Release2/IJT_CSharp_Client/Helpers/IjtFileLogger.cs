#nullable enable

using System.Text;
using Microsoft.Extensions.Logging;

namespace IJT_CSharp_Client.Helpers;

/// <summary>
/// Writes method output payloads to domain-specific log files for offline inspection.
/// All files are valid JSON — always overwritten with the latest snapshot.
/// File names match the OPC UA output argument label for easy identification.
///
/// File layout (relative to executable):
///   logs/
///     result/result.json                                  - latest Result (GetLatestResult / GetResultById / event)
///     events/joining_system_event.json                    - latest JoiningSystemEvent received
///     joining_process/joining_process_list.json           - latest JoiningProcessList (GetJoiningProcessList)
///     joining_process/selected_joining_program.json       - latest SelectedJoiningProgram (GetSelectedJoiningProgram)
///     joint/joint_list.json                               - latest JointList (GetJointList)
///     joint/joint.json                                    - latest Joint (GetJoint)
///     entity_list/entity_list.json                        - latest EntityList (GetIdentifiers)
///     io_signals/io_signals.json                          - latest IOSignals (GetIOSignals / SetIOSignals)
///     assets/<Category>_<Name>.json                       - one file per subscribed asset object (full variable tree)
/// </summary>
public static class IjtFileLogger
{
    private static readonly ILogger _log = IjtLog.ForCategory("IJT.FileLogger");

    private static readonly string _defaultBaseDir =
        Path.Combine(AppContext.BaseDirectory, "logs");

    // Test code can override the log root per execution context without affecting
    // parallel tests or production callers in the same process.
    private static readonly AsyncLocal<string?> _baseDirOverride = new();

    private static string CurrentBaseDir => _baseDirOverride.Value ?? _defaultBaseDir;

    /// <summary>Overwrites result.json with the latest result payload.</summary>
    public static void WriteResult(string content) => WriteFile(ResultLogPath, content);

    /// <summary>Overwrites events/joining_system_event.json with the latest JoiningSystemEvent payload.</summary>
    public static void WriteEvent(string content) => WriteFile(EventLogPath, content);

    /// <summary>Overwrites joining_process_list.json with the given content.</summary>
    public static void WriteJoiningProcessList(string content) => WriteFile(JoiningProcessListLogPath, content);

    /// <summary>Overwrites selected_joining_program.json with the given content.</summary>
    public static void WriteSelectedProgram(string content) => WriteFile(SelectedProgramLogPath, content);

    /// <summary>Overwrites joint_list.json with the given content.</summary>
    public static void WriteJointList(string content) => WriteFile(JointListLogPath, content);

    /// <summary>Overwrites joint.json with the given content.</summary>
    public static void WriteJoint(string content) => WriteFile(JointLogPath, content);

    /// <summary>Overwrites entity_list.json with the given content.</summary>
    public static void WriteIdentifiers(string content) => WriteFile(IdentifiersLogPath, content);

    /// <summary>Overwrites io_signals.json with the given content.</summary>
    public static void WriteIOSignals(string content) => WriteFile(IOSignalsLogPath, content);

    /// <summary>
    /// Overwrites logs/assets/<paramref name="assetKey"/>.json with the full asset variable tree.
    /// One file per asset object instance — file name is sanitized to be filesystem-safe.
    /// </summary>
    public static void WriteAsset(string assetKey, string content) =>
        WriteFile(Path.Combine(AssetLogDir, $"{SanitizeFileName(assetKey)}.json"), content);

    private static string SanitizeFileName(string name)
    {
        var invalid = Path.GetInvalidFileNameChars();
        return string.Concat(name.Select(c => invalid.Contains(c) ? '_' : c));
    }

    /// <summary>Base log directory (relative to executable).</summary>
    public static string BaseLogDir => CurrentBaseDir;

    public static string ResultLogPath => Path.Combine(BaseLogDir, "result", "result.json");
    public static string EventLogPath => Path.Combine(BaseLogDir, "events", "joining_system_event.json");
    public static string JoiningProcessListLogPath => Path.Combine(BaseLogDir, "joining_process", "joining_process_list.json");
    public static string SelectedProgramLogPath => Path.Combine(BaseLogDir, "joining_process", "selected_joining_program.json");
    public static string JointListLogPath => Path.Combine(BaseLogDir, "joint", "joint_list.json");
    public static string JointLogPath => Path.Combine(BaseLogDir, "joint", "joint.json");
    public static string IdentifiersLogPath => Path.Combine(BaseLogDir, "entity_list", "entity_list.json");
    public static string IOSignalsLogPath => Path.Combine(BaseLogDir, "io_signals", "io_signals.json");
    public static string AssetLogDir => Path.Combine(BaseLogDir, "assets");

    /// <summary>
    /// Temporarily overrides the base log directory for the current execution context.
    /// Intended for tests that need isolated file paths while the rest of the process keeps
    /// using the default runtime log root.
    /// </summary>
    internal static IDisposable PushBaseLogDirOverride(string baseDir)
    {
        var previous = _baseDirOverride.Value;
        _baseDirOverride.Value = baseDir;
        return new BaseLogDirOverrideScope(previous);
    }

    // Single lock for all file writes — event callbacks and menu calls can race on the same file.
    private static readonly object _fileLock = new();

    private sealed class BaseLogDirOverrideScope(string? previous) : IDisposable
    {
        public void Dispose()
        {
            _baseDirOverride.Value = previous;
        }
    }

    private static void WriteFile(string path, string content)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            lock (_fileLock)
                File.WriteAllText(path, content, Encoding.UTF8);
        }
        catch (IOException ex) { _log.LogWarning("Write failed: {Message}", ex.Message); }
        catch (UnauthorizedAccessException ex) { _log.LogWarning("Access denied: {Message}", ex.Message); }
    }
}
