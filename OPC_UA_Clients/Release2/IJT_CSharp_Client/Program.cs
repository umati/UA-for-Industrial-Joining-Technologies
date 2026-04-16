#nullable enable

using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Configuration;
using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;

using var cts = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) => { e.Cancel = true; cts.Cancel(); };

var _log = IjtLog.ForCategory("IJT.Client");

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

    // ── Event handlers — all output through logger, no Console calls ───────────
    js.EventSubscriber.OnResultReady += (_, e) =>
    {
        _log.LogInformation("Result received | {Name} | Seq#{Seq} | {Class} | {Time:HH:mm:ss}",
            e.Name ?? e.ResultId, e.SequenceNumber, e.Classification, e.EventTime);
        var text = e.Result is not null
            ? IjtResultFormatter.FormatResult(e.Result, e.EventTime)
            : IjtResultFormatter.FormatResultEventFields(
                e.ResultId, e.Classification, e.Name, e.SequenceNumber, e.AssemblyType, e.EventTime);
        _log.LogInformation("{ResultText}", text);
        IjtFileLogger.WriteResult(text);
        _log.LogInformation("Result logged to: {Path}", IjtFileLogger.ResultLogPath);
    };

    js.EventSubscriber.OnJoiningSystemEvent += (_, e) =>
    {
        _log.LogInformation("System event | Code:{Code} | {Text} | {Time:HH:mm:ss}",
            e.EventCode, e.EventText, e.EventTime);
        var text = IjtEventFormatter.FormatJoiningSystemEvent(
            e.EventCode, e.EventText, e.JoiningTechnology, e.EventTime,
            e.AssociatedEntities, e.ReportedValues);
        _log.LogInformation("{EventText}", text);
        IjtFileLogger.WriteEvent(text);
        _log.LogInformation("Event logged to: {Path}", IjtFileLogger.EventLogPath);
    };

    // ── Main menu loop ─────────────────────────────────────────────────────────
    var showMenu = true;
    while (!cts.Token.IsCancellationRequested)
    {
        if (showMenu)
        {
            PrintMenu(js, config.ServerUrl);
            showMenu = false;
        }

        Console.Write("  Command: ");

        string raw;
        try { raw = Console.ReadLine() ?? "0"; }
        catch (InvalidOperationException) { break; }

        var cmd = raw.Trim();

        if (string.IsNullOrEmpty(cmd) || cmd.Equals("m", StringComparison.OrdinalIgnoreCase))
        {
            showMenu = true;
            continue;
        }

        PrintCommandUsage(cmd);

        switch (cmd)
        {
            // ── SUBSCRIPTIONS (toggle) ─────────────────────────────────────────
            case "1":
                if (js.EventSubscriber.IsSubscribed)
                    js.EventSubscriber.Unsubscribe();
                else
                {
                    js.EventSubscriber.Subscribe();
                    _log.LogInformation("Result log: {P}", IjtFileLogger.ResultLogPath);
                    _log.LogInformation("Event  log: {P}", IjtFileLogger.EventLogPath);
                }
                showMenu = true;
                break;
            case "2":
                if (js.ResultManagement.IsResultVarSubscribed)
                    js.ResultManagement.StopResultVariableSubscription();
                else
                    js.ResultManagement.SubscribeResultVariable();
                showMenu = true;
                break;
            case "3":
                if (js.AssetManagement.IsAssetVarSubscribed)
                    js.AssetManagement.StopAssetVariableSubscription();
                else
                    js.AssetManagement.SubscribeAssetVariables();
                showMenu = true;
                break;

            // ── RESULT MANAGEMENT ─────────────────────────────────────────────
            case "4":
                js.ResultManagement.GetLatestResult();
                break;
            case "5":
                {
                    var rid = Prompt("Result ID");
                    if (rid != null) js.ResultManagement.GetResultById(rid);
                    break;
                }

            // ── ASSET MANAGEMENT ──────────────────────────────────────────────
            case "6":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri is null) break;
                    Console.Write("  Enable? [Y/n]: ");
                    var ynRaw = (Console.ReadLine() ?? "y").Trim();
                    js.AssetManagement.EnableAsset(uri,
                        !ynRaw.Equals("n", StringComparison.OrdinalIgnoreCase));
                    break;
                }
            case "7":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri is null) break;
                    var idsRaw = Prompt("Identifiers (comma-separated)");
                    if (idsRaw is null) break;
                    var ids = idsRaw.Split(',',
                        StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
                    js.AssetManagement.SendTextIdentifiers(uri, ids);
                    break;
                }
            case "8":
                {
                    var uri = Prompt("ProductInstance URI") ?? "";
                    var countStr = Prompt("How many entities? [1-10]");
                    if (countStr is null || !int.TryParse(countStr, out var entCount)
                        || entCount < 1 || entCount > 10)
                    { _log.LogWarning("Enter a number between 1 and 10."); break; }

                    var entities = new List<UAModel.IJTBase.EntityDataType>();
                    bool entityOk = true;
                    for (int ei = 0; ei < entCount && entityOk; ei++)
                    {
                        _log.LogInformation("── Entity {N} of {Total} ──", ei + 1, entCount);
                        var entityId = Prompt("  EntityId (required)");
                        if (entityId is null) { entityOk = false; break; }
                        IjtEntityTypes.PrintTable();
                        var etRaw = Prompt("  EntityType (enter number)");
                        if (etRaw is null) { entityOk = false; break; }
                        if (!short.TryParse(etRaw, out var entityType))
                        { _log.LogWarning("Invalid EntityType number."); entityOk = false; break; }
                        _log.LogInformation("EntityType: {Name}", IjtEntityTypes.Resolve(entityType));
                        var entityName = PromptOptional("  Name");
                        if (entityName is null) { entityOk = false; break; }
                        var entityDesc = PromptOptional("  Description");
                        if (entityDesc is null) { entityOk = false; break; }
                        var entityOid = PromptOptional("  EntityOriginId");
                        if (entityOid is null) { entityOk = false; break; }
                        var isExtRaw = PromptOptional("  IsExternal [y/n]");
                        if (isExtRaw is null) { entityOk = false; break; }
                        bool? isExt = isExtRaw.Equals("y", StringComparison.OrdinalIgnoreCase) ? true
                                    : isExtRaw.Equals("n", StringComparison.OrdinalIgnoreCase) ? false
                                    : (bool?)null;
                        entities.Add(UAModel.IJTBase.EntityDataType.Create(
                            entityId: entityId,
                            entityType: entityType,
                            name: string.IsNullOrEmpty(entityName) ? null : entityName,
                            description: string.IsNullOrEmpty(entityDesc) ? null : entityDesc,
                            entityOriginId: string.IsNullOrEmpty(entityOid) ? null : entityOid,
                            isExternal: isExt));
                    }
                    if (entityOk && entities.Count > 0)
                        js.AssetManagement.SendIdentifiers(entities, uri);
                    break;
                }
            case "9":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri != null) js.AssetManagement.GetIdentifiers(uri);
                    break;
                }
            case "10":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri != null) js.AssetManagement.ResetIdentifiers(uri);
                    break;
                }

            // ── JOINING PROCESS MANAGEMENT ────────────────────────────────────
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
                    var name = PromptOptional("Selection name") ?? "";
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

            // ── JOINT MANAGEMENT ──────────────────────────────────────────────
            case "14":
                {
                    var uri = PromptOptional("ProductInstance URI");
                    if (uri is null) break;
                    js.JointManagement.GetJointList(uri);
                    break;
                }
            case "15":
                {
                    var uri = Prompt("ProductInstance URI");
                    var id = Prompt("Joint ID");
                    if (uri != null && id != null) js.JointManagement.GetJoint(uri, id);
                    break;
                }
            case "16":
                {
                    var uri = Prompt("ProductInstance URI") ?? "";
                    var id = Prompt("Joint ID");
                    var oid = Prompt("Joint Origin ID") ?? "";
                    if (id != null) js.JointManagement.SelectJoint(uri, id, oid);
                    break;
                }
            case "17":
                {
                    var uri = Prompt("ProductInstance URI") ?? "";
                    var id = Prompt("Joint ID");
                    var oid = Prompt("Joint Origin ID") ?? "";
                    if (id != null) js.JointManagement.DeleteJoint(uri, id, oid);
                    break;
                }
            case "18":
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
                _log.LogWarning("Unknown command '{Cmd}'. Press Enter to show menu.", cmd);
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
/// Returns empty string when the user presses Enter (skip).
/// Returns null when input exceeds maxLen — callers should abort.
/// </summary>
static string? PromptOptional(string label, int maxLen = 256)
{
    Console.Write($"  {label} (optional, Enter to skip): ");
    var v = Console.ReadLine()?.Trim();
    if (string.IsNullOrWhiteSpace(v)) return "";
    if (v.Length > maxLen) { Console.WriteLine($"  Input too long (max {maxLen} chars) — cancelled."); return null; }
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

/// <summary>
/// Draws the main menu. Subscription state is read live from the JoiningSystem
/// so the ON/off indicators are always accurate when the menu is shown.
/// </summary>
static void PrintMenu(JoiningSystem js, string serverUrl)
{
    var ev = js.EventSubscriber.IsSubscribed ? "ON " : "off";
    var rv = js.ResultManagement.IsResultVarSubscribed ? "ON " : "off";
    var av = js.AssetManagement.IsAssetVarSubscribed ? "ON " : "off";

    Console.WriteLine($"""

  Server: {serverUrl}
  ┌─────────────────────────────────────────────────────────┐
  │  SUBSCRIPTIONS  (toggle: press number to start/stop)    │
  │   1  IJT events          ResultReady + SystemEvents [{ev}] │
  │   2  Result variable     ResultManagement/Results   [{rv}] │
  │   3  Asset variables     AssetManagement/Assets     [{av}] │
  │                                                         │
  │  RESULT MANAGEMENT                                      │
  │   4  GetLatestResult                        > log      │
  │   5  GetResultById                          > log      │
  │                                                         │
  │  ASSET MANAGEMENT                                       │
  │   6  EnableAsset                                        │
  │   7  SendTextIdentifiers                                │
  │   8  SendIdentifiers (EntityDataType)                   │
  │   9  GetIdentifiers                         > log      │
  │  10  ResetIdentifiers                                   │
  │                                                         │
  │  JOINING PROCESS MANAGEMENT                             │
  │  11  GetJoiningProcessList                  > log      │
  │  12  SelectJoiningProcess                               │
  │  13  GetSelectedJoiningProgram              > log      │
  │                                                         │
  │  JOINT MANAGEMENT                                       │
  │  14  GetJointList                           > log      │
  │  15  GetJoint                               > log      │
  │  16  SelectJoint                                        │
  │  17  DeleteJoint                                        │
  │  18  SendJoint                                          │
  │                                                         │
  │   0  Quit            m / Enter = redraw this menu       │
  └─────────────────────────────────────────────────────────┘
  """);
}

static void PrintCommandUsage(string cmd)
{
    switch (cmd)
    {
        // SUBSCRIPTIONS
        case "1":
            IjtMenuHelper.PrintUsage(
                "Toggle IJT Events",
                "Subscribes or unsubscribes from ResultReady + JoiningSystemEvent on the Server node. " +
                "Events arrive asynchronously and are logged to logs/results/ and logs/events/.",
                [],
                ["Event notifications (ResultReady / JoiningSystemEvent)"]);
            break;
        case "2":
            IjtMenuHelper.PrintUsage(
                "Toggle Result Variable",
                "Subscribes or unsubscribes a data-change notification on " +
                "ResultManagement/Results/Result. Fires whenever a new result is written to the node.",
                [],
                ["Data-change notification > logs/results/result.log"]);
            break;
        case "3":
            IjtMenuHelper.PrintUsage(
                "Toggle Asset Variables",
                "Subscribes or unsubscribes data-change notifications on all " +
                "Identification variables (ProductInstanceUri, SerialNumber, Model, " +
                "Manufacturer, SoftwareRevision, HardwareRevision) under " +
                "AssetManagement/Assets/Controllers/* and .../Tools/*.",
                [],
                ["Data-change notifications per variable"]);
            break;
        // RESULT MANAGEMENT
        case "4":
            IjtMenuHelper.PrintUsage(
                "GetLatestResult",
                "Calls ResultManagement/MethodSet/GetLatestResult. " +
                "Full result logged to: logs/results/result.log",
                ["TimeoutMs: Int32 (default 5000)"],
                ["ResultHandle", "Result > logs/results/result.log", "Error"]);
            break;
        case "5":
            IjtMenuHelper.PrintUsage(
                "GetResultById",
                "Calls ResultManagement/MethodSet/GetResultById. " +
                "Full result logged to: logs/results/result.log",
                ["ResultId: String", "TimeoutMs: Int32 (default 5000)"],
                ["ResultHandle", "Result > logs/results/result.log", "Error"]);
            break;
        // ASSET MANAGEMENT
        case "6":
            IjtMenuHelper.PrintUsage(
                "EnableAsset",
                "Calls AssetManagement/MethodSet/EnableAsset. " +
                "Enables or disables the asset identified by ProductInstanceUri.",
                ["ProductInstanceUri: String", "Enable: Boolean"],
                ["Status", "StatusMessage"]);
            break;
        case "7":
            IjtMenuHelper.PrintUsage(
                "SendTextIdentifiers",
                "Calls AssetManagement/MethodSet/SendTextIdentifiers. " +
                "Sends plain string identifiers (e.g. barcodes, batch IDs) for an asset.",
                ["ProductInstanceUri: String", "Identifiers: String[]"],
                ["Status", "StatusMessage"]);
            break;
        case "8":
            IjtMenuHelper.PrintUsage(
                "SendIdentifiers",
                "Calls AssetManagement/MethodSet/SendIdentifiers. " +
                "Sends structured EntityDataType identifiers. " +
                "Prompts per entity: EntityId, EntityType (0-41), Name, Description, EntityOriginId, IsExternal.",
                ["ProductInstanceUri: String", "EntityList: EntityDataType[] (1-10 entries)"],
                ["Status", "StatusMessage"]);
            break;
        case "9":
            IjtMenuHelper.PrintUsage(
                "GetIdentifiers",
                "Calls AssetManagement/MethodSet/GetIdentifiers. " +
                "Pass empty IdentifierNames to retrieve ALL registered identifiers for the asset. " +
                "Full entity list logged to: logs/identifiers/identifiers.log",
                ["ProductInstanceUri: String", "IdentifierNames: String[] (empty = return all)"],
                ["EntityList > logs/identifiers/identifiers.log", "Status", "StatusMessage"]);
            break;
        case "10":
            IjtMenuHelper.PrintUsage(
                "ResetIdentifiers",
                "Calls AssetManagement/MethodSet/ResetIdentifiers. " +
                "Clears identifiers registered for the given product instance.",
                ["ProductInstanceUri: String"],
                ["Status", "StatusMessage"]);
            break;
        // JOINING PROCESS MANAGEMENT
        case "11":
            IjtMenuHelper.PrintUsage(
                "GetJoiningProcessList",
                "Calls JoiningProcessManagement/MethodSet/GetJoiningProcessList. " +
                "Full list logged to: logs/joining_process/process_list.log",
                ["ProductInstanceUri: String (optional)"],
                ["JoiningProcessList > logs/joining_process/process_list.log", "Status", "StatusMessage"]);
            break;
        case "12":
            IjtMenuHelper.PrintUsage(
                "SelectJoiningProcess",
                "Calls JoiningProcessManagement/MethodSet/SelectJoiningProcess.",
                ["JoiningProcessId: String", "SelectionName: String (optional)"],
                ["Status", "StatusMessage"]);
            break;
        case "13":
            IjtMenuHelper.PrintUsage(
                "GetSelectedJoiningProgram",
                "Calls JoiningProcessManagement/MethodSet/GetSelectedJoiningProgram. " +
                "Full data logged to: logs/joining_process/selected_program.log",
                ["ProductInstanceUri: String (optional)"],
                ["SelectedJoiningProgram > logs/joining_process/selected_program.log", "Status", "StatusMessage"]);
            break;
        // JOINT MANAGEMENT
        case "14":
            IjtMenuHelper.PrintUsage(
                "GetJointList",
                "Calls JointManagement/MethodSet/GetJointList. " +
                "Full list logged to: logs/joints/joint_list.log",
                ["ProductInstanceUri: String (optional)"],
                ["JointList > logs/joints/joint_list.log", "Status", "StatusMessage"]);
            break;
        case "15":
            IjtMenuHelper.PrintUsage(
                "GetJoint",
                "Calls JointManagement/MethodSet/GetJoint. " +
                "Full joint data logged to: logs/joints/joint.log",
                ["ProductInstanceUri: String", "JointId: NormalizedString"],
                ["Joint > logs/joints/joint.log", "Status", "StatusMessage"]);
            break;
        case "16":
            IjtMenuHelper.PrintUsage(
                "SelectJoint",
                "Calls JointManagement/MethodSet/SelectJoint.",
                ["ProductInstanceUri: String", "JointId: NormalizedString", "JointOriginId: NormalizedString"],
                ["Status", "StatusMessage"]);
            break;
        case "17":
            IjtMenuHelper.PrintUsage(
                "DeleteJoint",
                "Calls JointManagement/MethodSet/DeleteJoint.",
                ["ProductInstanceUri: String", "JointId: NormalizedString", "JointOriginId: NormalizedString"],
                ["Status", "StatusMessage"]);
            break;
        case "18":
            IjtMenuHelper.PrintUsage(
                "SendJoint",
                "Calls JointManagement/MethodSet/SendJoint.",
                ["ProductInstanceUri: String", "JointId: String", "JointDesignId: String"],
                ["Status", "StatusMessage"]);
            break;
    }
}
