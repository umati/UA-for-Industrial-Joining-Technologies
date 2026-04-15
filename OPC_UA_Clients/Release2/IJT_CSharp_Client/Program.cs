#nullable enable

using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Configuration;
using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;

using var cts = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) => { e.Cancel = true; cts.Cancel(); };

var _log = IjtLog.ForCategory("IJT.Client");
var _subscribed = false;

PrintBanner();

// ── Configuration & connect ────────────────────────────────────────────────────
var config = ClientConfig.FromEnvironment();

JoiningSystem? js;
try
{
    _log.LogInformation("Connecting to {Url} …", config.ServerUrl);
    js = await JoiningSystem.ConnectAsync(config, cts.Token);
}
catch (Opc.Ua.ServiceResultException srex)
{
    _log.LogError("Connection failed [{Status}]: {Msg}",
        IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
    IjtLog.Shutdown(); return 1;
}
catch (Exception ex)
{
    _log.LogError(ex, "Connection failed");
    IjtLog.Shutdown(); return 1;
}

await using (js)
{
    _log.LogInformation("✓ Connected. Log files: {Dir}", IjtFileLogger.BaseLogDir);

    // ── Wire up event handlers ─────────────────────────────────────────────────
    js.EventSubscriber.OnResultReady += (_, e) =>
    {
        _log.LogInformation("Result received | {Name} | Seq#{Seq} | {Class} | {Time:HH:mm:ss}",
            e.Name ?? e.ResultId, e.SequenceNumber, e.Classification, e.EventTime);
        _log.LogInformation("Result logged to: {Path}", IjtFileLogger.ResultLogPath);

        var text = e.Result is not null
            ? IjtResultFormatter.FormatResult(e.Result, e.EventTime)
            : IjtResultFormatter.FormatResultEventFields(
                e.ResultId, e.Classification, e.Name, e.SequenceNumber, e.AssemblyType, e.EventTime);
        IjtFileLogger.WriteResult(text);
    };

    js.EventSubscriber.OnJoiningSystemEvent += (_, e) =>
    {
        _log.LogInformation("System event | Code:{Code} | {Text} | {Time:HH:mm:ss}",
            e.EventCode, e.EventText, e.EventTime);
        _log.LogInformation("Event logged to: {Path}", IjtFileLogger.EventLogPath);

        var text = IjtEventFormatter.FormatJoiningSystemEvent(
            e.EventCode, e.EventText, e.JoiningTechnology, e.EventTime,
            e.AssociatedEntities, e.ReportedValues);
        IjtFileLogger.WriteEvent(text);
    };

    // ── Main menu loop ─────────────────────────────────────────────────────────
    while (!cts.Token.IsCancellationRequested)
    {
        PrintMenu(_subscribed, config.ServerUrl);

        string raw;
        try { raw = Console.ReadLine() ?? "0"; }
        catch (InvalidOperationException) { break; }

        var cmd = raw.Trim();
        PrintCommandUsage(cmd);

        switch (cmd)
        {
            // Events
            case "1":
                js.EventSubscriber.Subscribe();
                _subscribed = true;
                _log.LogInformation("Subscribed to result and system events.");
                _log.LogInformation("Result log: {P}", IjtFileLogger.ResultLogPath);
                _log.LogInformation("Event  log: {P}", IjtFileLogger.EventLogPath);
                break;
            case "2":
                js.EventSubscriber.Unsubscribe();
                _subscribed = false;
                break;

            // Results
            case "3":
                js.ResultManagement.GetLatestResult();
                break;
            case "4":
                {
                    var rid = Prompt("Result ID");
                    if (rid != null) js.ResultManagement.GetResultById(rid);
                    break;
                }
            case "5":
                js.ResultManagement.SubscribeResultVariable();
                break;

            // Asset Management
            case "6":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri is null) break;
                    Console.Write("  Enable? [Y/n]: ");
                    var ynRaw = (Console.ReadLine() ?? "y").Trim();
                    var yn = ynRaw.Length > 10 ? "y" : ynRaw;
                    js.AssetManagement.EnableAsset(uri, !yn.Equals("n", StringComparison.OrdinalIgnoreCase));
                    break;
                }
            case "7":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri != null) js.AssetManagement.SendTextIdentifiers(uri, ["ID-001", "Batch-2024"]);
                    break;
                }
            case "8":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri != null) js.AssetManagement.GetIdentifiers(uri);
                    break;
                }
            case "9":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri != null) js.AssetManagement.ResetIdentifiers(uri);
                    break;
                }
            case "10":
                js.AssetManagement.SubscribeAssetVariables();
                break;

            // Joining Process
            case "11":
                {
                    var uri = PromptOptional("ProductInstance URI");
                    if (uri is null) break;
                    js.JoiningProcessManagement.GetJoiningProcessList(uri);
                    break;
                }
            case "12":
                {
                    var id = Prompt("Joining Process ID");
                    if (id is null) break;
                    var name = Prompt("Selection name (optional, press Enter to skip)") ?? "";
                    js.JoiningProcessManagement.SelectJoiningProcess(id, selectionName: name);
                    break;
                }
            case "13":
                {
                    var uri = PromptOptional("ProductInstance URI");
                    if (uri is null) break;
                    js.JoiningProcessManagement.GetSelectedJoiningProgram(uri);
                    break;
                }

            // Identifiers demo
            case "14":
                {
                    var entities = new List<UAModel.IJTBase.EntityDataType>
                    {
                        new() { Name = "Batch-A", EntityId = "ENT-001", IsExternal = false, EntityType = 0 }
                    };
                    js.AssetManagement.SendIdentifiers(entities);
                    break;
                }

            // Joint Management
            case "15":
                {
                    var uri = PromptOptional("ProductInstance URI");
                    if (uri is null) break;
                    js.JointManagement.GetJointList(uri);
                    break;
                }
            case "16":
                {
                    var uri = Prompt("ProductInstance URI");
                    var id = Prompt("Joint ID");
                    if (uri != null && id != null) js.JointManagement.GetJoint(uri, id);
                    break;
                }
            case "17":
                {
                    var uri = Prompt("ProductInstance URI") ?? "";
                    var id = Prompt("Joint ID");
                    var oid = Prompt("Joint Origin ID") ?? "";
                    if (id != null) js.JointManagement.SelectJoint(uri, id, oid);
                    break;
                }
            case "18":
                {
                    var uri = Prompt("ProductInstance URI") ?? "";
                    var id = Prompt("Joint ID");
                    var oid = Prompt("Joint Origin ID") ?? "";
                    if (id != null) js.JointManagement.DeleteJoint(uri, id, oid);
                    break;
                }
            case "19":
                {
                    var uri = Prompt("ProductInstance URI") ?? "";
                    var id = Prompt("Joint ID");
                    var did = Prompt("Joint Design ID") ?? "";
                    if (id != null) js.JointManagement.SendJoint(uri, id, did);
                    break;
                }

            case "0":
                cts.Cancel();
                break;

            default:
                _log.LogWarning("Unknown command '{Cmd}'. Enter a number from the menu.", cmd);
                break;
        }
    }
}

_log.LogInformation("Disconnected. Goodbye.");
IjtLog.Shutdown();
return 0;

// ── Helpers ───────────────────────────────────────────────────────────────────

static string? Prompt(string label, int maxLen = 256)
{
    Console.Write($"  {label}: ");
    var v = Console.ReadLine()?.Trim();
    if (string.IsNullOrWhiteSpace(v)) return null;
    if (v.Length > maxLen) { Console.WriteLine($"  Input too long (max {maxLen})."); return null; }
    return v;
}

/// <summary>
/// Prompts for an optional input value.
/// Returns empty string <c>""</c> when the user presses Enter (skip → use default).
/// Returns <c>null</c> when input exceeds <paramref name="maxLen"/> — callers should abort the command.
/// </summary>
static string? PromptOptional(string label, int maxLen = 256)
{
    Console.Write($"  {label} (optional, Enter to skip): ");
    var v = Console.ReadLine()?.Trim();
    if (string.IsNullOrWhiteSpace(v)) return "";
    if (v.Length > maxLen) { Console.WriteLine($"  Input too long (max {maxLen} chars) — command cancelled."); return null; }
    return v;
}

static void PrintBanner()
{
    Console.WriteLine();
    Console.WriteLine("  ╔══════════════════════════════════════════════════╗");
    Console.WriteLine("  ║   IJT OPC UA Client  —  C# Reference Example    ║");
    Console.WriteLine("  ║   OPC UA for Industrial Joining Technologies     ║");
    Console.WriteLine("  ╚══════════════════════════════════════════════════╝");
    Console.WriteLine();
}

static void PrintMenu(bool subscribed, string serverUrl)
{
    var subStatus = subscribed ? "[active]" : "[inactive]";
    Console.WriteLine($"""

  Server: {serverUrl}
  ┌──────────────────────────────────────────────────┐
  │  EVENTS  (subscription: {subStatus,-10})              │
  │   1  Subscribe to Result + System events          │
  │   2  Unsubscribe                                  │
  │                                                   │
  │  RESULT MANAGEMENT                                │
  │   3  Get latest result               → log       │
  │   4  Get result by ID                → log       │
  │   5  Subscribe result variable                    │
  │                                                   │
  │  ASSET MANAGEMENT                                 │
  │   6  Enable / disable asset                       │
  │   7  Send text identifiers (demo)                 │
  │   8  Get identifiers                 → log       │
  │   9  Reset identifiers                            │
  │  10  Subscribe asset variables                    │
  │                                                   │
  │  JOINING PROCESS                                  │
  │  11  Get joining process list        → log       │
  │  12  Select joining process                       │
  │  13  Get selected joining program    → log       │
  │  14  Send identifiers (EntityDataType demo)       │
  │                                                   │
  │  JOINT MANAGEMENT                                 │
  │  15  Get joint list                  → log       │
  │  16  Get joint                       → log       │
  │  17  Select joint                                 │
  │  18  Delete joint                                 │
  │  19  Send joint                                   │
  │                                                   │
  │   0  Quit                                         │
  └──────────────────────────────────────────────────┘
  """);
    Console.Write("  Command: ");
}

static void PrintCommandUsage(string cmd)
{
    switch (cmd)
    {
        case "1":
            IjtMenuHelper.PrintUsage(
                "Subscribe",
                "Subscribe to Result + JoiningSystem events on the server node.",
                [],
                ["Event notifications (ResultReady/JoiningSystemEvent)"]);
            break;
        case "2":
            IjtMenuHelper.PrintUsage(
                "Unsubscribe",
                "Stop active event subscriptions.",
                [],
                ["Subscription stopped"]);
            break;
        case "3":
            IjtMenuHelper.PrintUsage(
                "GetLatestResult",
                "Fetch latest result from ResultManagement. Full result logged to: logs/results/result.log",
                ["TimeoutMs: Int32 (default 5000)"],
                ["ResultHandle", "Result → logs/results/result.log", "Error"]);
            break;
        case "4":
            IjtMenuHelper.PrintUsage(
                "GetResultById",
                "Fetch result by ResultId. Full result logged to: logs/results/result.log",
                ["ResultId: String", "TimeoutMs: Int32 (default 5000)"],
                ["ResultHandle", "Result → logs/results/result.log", "Error"]);
            break;
        case "5":
            IjtMenuHelper.PrintUsage(
                "SubscribeResultVariable",
                "Subscribe to live Result variable data changes.",
                [],
                ["Data-change notifications"]);
            break;
        case "6":
            IjtMenuHelper.PrintUsage(
                "EnableAsset",
                "Enable or disable a product instance.",
                ["ProductInstanceUri: String", "Enable: Boolean"],
                ["Status", "StatusMessage"]);
            break;
        case "7":
            IjtMenuHelper.PrintUsage(
                "SendTextIdentifiers",
                "Send textual identifiers for a product instance.",
                ["ProductInstanceUri: String", "Identifiers: String[]"],
                ["Status", "StatusMessage"]);
            break;
        case "8":
            IjtMenuHelper.PrintUsage(
                "GetIdentifiers",
                "Read identifiers for a product instance. Full list logged to: logs/identifiers/identifiers.log",
                ["ProductInstanceUri: String"],
                ["EntityList → logs/identifiers/identifiers.log", "Status", "StatusMessage"]);
            break;
        case "9":
            IjtMenuHelper.PrintUsage(
                "ResetIdentifiers",
                "Reset identifiers for a product instance.",
                ["ProductInstanceUri: String"],
                ["Status", "StatusMessage"]);
            break;
        case "10":
            IjtMenuHelper.PrintUsage(
                "SubscribeAssetVariables",
                "Subscribe to identification variables under assets.",
                [],
                ["Data-change notifications"]);
            break;
        case "11":
            IjtMenuHelper.PrintUsage(
                "GetJoiningProcessList",
                "Read available joining processes. Full list logged to: logs/joining_process/process_list.log",
                ["ProductInstanceUri: String (optional)"],
                ["JoiningProcessList → logs/joining_process/process_list.log", "Status", "StatusMessage"]);
            break;
        case "12":
            IjtMenuHelper.PrintUsage(
                "SelectJoiningProcess",
                "Select joining process to use.",
                ["JoiningProcessId: String", "SelectionName: String (optional)"],
                ["Status", "StatusMessage"]);
            break;
        case "13":
            IjtMenuHelper.PrintUsage(
                "GetSelectedJoiningProgram",
                "Read currently selected joining program. Full data logged to: logs/joining_process/selected_program.log",
                ["ProductInstanceUri: String (optional)"],
                ["SelectedJoiningProgram → logs/joining_process/selected_program.log", "Status", "StatusMessage"]);
            break;
        case "14":
            IjtMenuHelper.PrintUsage(
                "SendIdentifiers",
                "Send EntityDataType identifiers (demo path).",
                ["EntityList: EntityDataType[]", "ProductInstanceUri: String (optional)"],
                ["Status", "StatusMessage"]);
            break;
        case "15":
            IjtMenuHelper.PrintUsage(
                "GetJointList",
                "Read joint list. Full list logged to: logs/joints/joint_list.log",
                ["ProductInstanceUri: String (optional)"],
                ["JointList → logs/joints/joint_list.log", "Status", "StatusMessage"]);
            break;
        case "16":
            IjtMenuHelper.PrintUsage(
                "GetJoint",
                "Read one joint by JointId. Full joint data logged to: logs/joints/joint.log",
                ["ProductInstanceUri: String", "JointId: NormalizedString"],
                ["Joint → logs/joints/joint.log", "Status", "StatusMessage"]);
            break;
        case "17":
            IjtMenuHelper.PrintUsage(
                "SelectJoint",
                "Select joint for product instance.",
                ["ProductInstanceUri: String", "JointId: NormalizedString", "JointOriginId: NormalizedString"],
                ["Status", "StatusMessage"]);
            break;
        case "18":
            IjtMenuHelper.PrintUsage(
                "DeleteJoint",
                "Delete joint association.",
                ["ProductInstanceUri: String", "JointId: NormalizedString", "JointOriginId: NormalizedString"],
                ["Status", "StatusMessage"]);
            break;
        case "19":
            IjtMenuHelper.PrintUsage(
                "SendJoint",
                "Send joint definition to server.",
                ["ProductInstanceUri: String", "Joint: JointDataType"],
                ["Status", "StatusMessage"]);
            break;
    }
}
