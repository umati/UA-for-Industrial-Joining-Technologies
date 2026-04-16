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

    private static readonly string _baseDir =
        Path.Combine(AppContext.BaseDirectory, "logs");

    private static readonly string _resultLogPath =
        Path.Combine(_baseDir, "result", "result.json");

    private static readonly string _eventLogPath =
        Path.Combine(_baseDir, "events", "joining_system_event.json");

    private static readonly string _joiningProcessListLogPath =
        Path.Combine(_baseDir, "joining_process", "joining_process_list.json");

    private static readonly string _selectedProgramLogPath =
        Path.Combine(_baseDir, "joining_process", "selected_joining_program.json");

    private static readonly string _jointListLogPath =
        Path.Combine(_baseDir, "joint", "joint_list.json");

    private static readonly string _jointLogPath =
        Path.Combine(_baseDir, "joint", "joint.json");

    private static readonly string _identifiersLogPath =
        Path.Combine(_baseDir, "entity_list", "entity_list.json");

    private static readonly string _ioSignalsLogPath =
        Path.Combine(_baseDir, "io_signals", "io_signals.json");

    private static readonly string _assetLogDir =
        Path.Combine(_baseDir, "assets");

    /// <summary>Overwrites result.json with the latest result payload.</summary>
    public static void WriteResult(string content) => WriteFile(_resultLogPath, content);

    /// <summary>Overwrites events/joining_system_event.json with the latest JoiningSystemEvent payload.</summary>
    public static void WriteEvent(string content) => WriteFile(_eventLogPath, content);

    /// <summary>Overwrites joining_process_list.json with the given content.</summary>
    public static void WriteJoiningProcessList(string content) => WriteFile(_joiningProcessListLogPath, content);

    /// <summary>Overwrites selected_joining_program.json with the given content.</summary>
    public static void WriteSelectedProgram(string content) => WriteFile(_selectedProgramLogPath, content);

    /// <summary>Overwrites joint_list.json with the given content.</summary>
    public static void WriteJointList(string content) => WriteFile(_jointListLogPath, content);

    /// <summary>Overwrites joint.json with the given content.</summary>
    public static void WriteJoint(string content) => WriteFile(_jointLogPath, content);

    /// <summary>Overwrites entity_list.json with the given content.</summary>
    public static void WriteIdentifiers(string content) => WriteFile(_identifiersLogPath, content);

    /// <summary>Overwrites io_signals.json with the given content.</summary>
    public static void WriteIOSignals(string content) => WriteFile(_ioSignalsLogPath, content);

    /// <summary>
    /// Overwrites logs/assets/<paramref name="assetKey"/>.json with the full asset variable tree.
    /// One file per asset object instance — file name is sanitized to be filesystem-safe.
    /// </summary>
    public static void WriteAsset(string assetKey, string content) =>
        WriteFile(Path.Combine(_assetLogDir, $"{SanitizeFileName(assetKey)}.json"), content);

    private static string SanitizeFileName(string name)
    {
        var invalid = Path.GetInvalidFileNameChars();
        return string.Concat(name.Select(c => invalid.Contains(c) ? '_' : c));
    }

    /// <summary>Base log directory (relative to executable).</summary>
    public static string BaseLogDir => _baseDir;

    public static string ResultLogPath => _resultLogPath;
    public static string EventLogPath => _eventLogPath;
    public static string JoiningProcessListLogPath => _joiningProcessListLogPath;
    public static string SelectedProgramLogPath => _selectedProgramLogPath;
    public static string JointListLogPath => _jointListLogPath;
    public static string JointLogPath => _jointLogPath;
    public static string IdentifiersLogPath => _identifiersLogPath;
    public static string IOSignalsLogPath => _ioSignalsLogPath;
    public static string AssetLogDir => _assetLogDir;

    // Single lock for all file writes — event callbacks and menu calls can race on the same file.
    private static readonly object _fileLock = new();

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
