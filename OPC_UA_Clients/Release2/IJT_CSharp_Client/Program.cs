#nullable enable

using System.Text;
using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Configuration;
using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;

using var cts = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) => { e.Cancel = true; cts.Cancel(); };

var _log = IjtLog.ForCategory("IJT.Client");

Console.OutputEncoding = Encoding.UTF8;
Console.InputEncoding = Encoding.UTF8;

PrintBanner();

// ── Configuration & connect ────────────────────────────────────────────────────
var config = ClientConfig.FromEnvironment();

JoiningSystem? js;
try
{
    _log.LogInformation("Connecting to {Url} ...", config.ServerUrl);
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
    _log.LogInformation("Connected. Log files: {Dir}", IjtFileLogger.BaseLogDir);

    // ── Event handlers — all output through logger, no Console calls ───────────
    js.EventSubscriber.OnResultReady += (_, e) =>
    {
        _log.LogInformation("Result received | {Name} | Seq#{Seq} | {Class} | {Time:HH:mm:ss}",
            e.Name ?? e.ResultId, e.SequenceNumber, e.Classification, e.EventTime);
        var text = e.Result is not null
            ? IjtResultFormatter.FormatResult(e.Result, e.EventTime)
            : IjtResultFormatter.FormatResultEventFields(
                e.ResultId, e.Classification, e.Name, e.SequenceNumber, e.AssemblyType, e.EventTime);
        IjtFileLogger.WriteResult(text);
        _log.LogInformation("Result logged to: {Path}", IjtFileLogger.ResultLogPath);
    };

    js.EventSubscriber.OnJoiningSystemEvent += (_, e) =>
    {
        _log.LogInformation("System event | Code:{Code} | {Text} | {Time:HH:mm:ss}",
            e.EventCode, e.EventText, e.EventTime);
        var json = IjtEventFormatter.SerializeEventJson(
            e.EventCode, e.EventText, e.JoiningTechnology, e.EventTime,
            e.AssociatedEntities, e.ReportedValues);
        IjtFileLogger.WriteEvent(json);
        _log.LogInformation("Event logged to: {Path}", IjtFileLogger.EventLogPath);
    };

    // -- Main menu loop ---------------------------------------------------------
    var showMenu = true;
    while (!cts.Token.IsCancellationRequested)
    {
        if (showMenu)
        {
            PrintMenu(js, config.ServerUrl);
            showMenu = false;
        }

        lock (IJT_CSharp_Client.Helpers.IjtLog.ConsoleLock)
        {
            Console.WriteLine();
            Console.WriteLine("  Enter command (0-36, m=menu, h=help), then press Enter:");
            Console.Write("  > ");
        }

        string raw;
        try { raw = Console.ReadLine() ?? "0"; }
        catch (InvalidOperationException) { break; }

        var cmd = raw.Trim();

        if (string.IsNullOrEmpty(cmd) || cmd.Equals("m", StringComparison.OrdinalIgnoreCase))
        {
            showMenu = true;
            continue;
        }

        if (cmd.Equals("h", StringComparison.OrdinalIgnoreCase) || cmd.Equals("help", StringComparison.OrdinalIgnoreCase))
        {
            var helpCmd = Prompt("Show usage for command number");
            if (!string.IsNullOrEmpty(helpCmd))
                PrintCommandUsage(helpCmd);
            continue;
        }

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
                    var enabled = PromptBool("Enable", defaultYes: true);
                    js.AssetManagement.EnableAsset(uri, enabled);
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

                    IjtEntityTypes.PrintTable();
                    var entities = new List<UAModel.IJTBase.EntityDataType>();
                    bool entityOk = true;
                    for (int ei = 0; ei < entCount && entityOk; ei++)
                    {
                        Console.WriteLine();
                        Console.WriteLine($"  -- Entity {ei + 1} of {entCount} --");
                        var entityId = Prompt("  EntityId (required)");
                        if (entityId is null) { entityOk = false; break; }
                        var etRaw = Prompt("  EntityType (enter number)");
                        if (etRaw is null) { entityOk = false; break; }
                        if (!short.TryParse(etRaw, out var entityType))
                        { _log.LogWarning("Invalid EntityType number."); entityOk = false; break; }
                        Console.WriteLine($"  EntityType: {IjtEntityTypes.Resolve(entityType)}");
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

            // ── JOINING PROCESS MANAGEMENT – EXTENDED ─────────────────────────
            case "19":
                {
                    var uri = Prompt("ProductInstance URI (Tool URI)");
                    if (uri is null) break;
                    var deselect = PromptBool("Deselect after joining", defaultYes: false);
                    js.JoiningProcessManagement.StartSelectedJoining(uri, deselect);
                    break;
                }
            case "20":
                {
                    var uri = Prompt("ProductInstance URI (Tool URI, e.g. www.atlascopco.com/...)");
                    var id = Prompt("Joining Process ID (e.g. 0952E9B4-05F6-4B43-B66C-B8027FBE966A)");
                    if (uri is null || id is null) break;
                    var oid = PromptOptional("Joining Process Origin ID") ?? "";
                    // PROGRAM entity — key entity describing which program to start
                    var progOrigin = PromptOptional("Program EntityOriginId (e.g. DCCA6C76-3926-455B-959B-EA3082FCD091)") ?? "";
                    var entities = new List<UAModel.IJTBase.EntityDataType>
                    {
                        UAModel.IJTBase.EntityDataType.Create(
                            id, entityType: (short)27,
                            name: "ProgramId", description: "Program_4_Steps",
                            entityOriginId: string.IsNullOrEmpty(progOrigin) ? null : progOrigin,
                            isExternal: false),
                    };
                    // Optional VIN — external identifier for the vehicle/product being joined
                    var vin = PromptOptional("VIN (VEHICLE entity, e.g. 4Y1SL65848Z411439, Enter to skip)") ?? "";
                    if (!string.IsNullOrEmpty(vin))
                        entities.Add(UAModel.IJTBase.EntityDataType.Create(
                            vin, entityType: (short)20,
                            name: "VIN", description: "Vehicle Identification Number",
                            isExternal: true));
                    js.JoiningProcessManagement.StartJoiningProcess(uri, id, oid, entities);
                    break;
                }
            case "21":
                {
                    var uri = Prompt("ProductInstance URI");
                    var id = Prompt("Joining Process ID");
                    if (uri is null || id is null) break;
                    var oid = PromptOptional("Joining Process Origin ID") ?? "";
                    var msg = PromptOptional("Abort message") ?? "";
                    js.JoiningProcessManagement.AbortJoiningProcess(uri, id, oid, msg);
                    break;
                }
            case "22":
                {
                    var uri = PromptOptional("ProductInstance URI") ?? "";
                    js.JoiningProcessManagement.DeselectJoiningProcess(uri);
                    break;
                }
            case "23":
                {
                    var uri = Prompt("ProductInstance URI");
                    var id = Prompt("Joining Process ID");
                    if (uri is null || id is null) break;
                    var oid = PromptOptional("Joining Process Origin ID") ?? "";
                    js.JoiningProcessManagement.ResetJoiningProcess(uri, id, oid);
                    break;
                }
            case "24":
                {
                    var uri = Prompt("ProductInstance URI");
                    var id = Prompt("Joining Process ID");
                    if (uri is null || id is null) break;
                    var cntRaw = PromptOptional("Increment count (Enter=1)") ?? "1";
                    if (!uint.TryParse(cntRaw, out var cnt)) cnt = 1;
                    var oid = PromptOptional("Joining Process Origin ID") ?? "";
                    js.JoiningProcessManagement.IncrementJoiningProcessCounter(uri, id, cnt, oid);
                    break;
                }
            case "25":
                {
                    var uri = Prompt("ProductInstance URI");
                    var id = Prompt("Joining Process ID");
                    if (uri is null || id is null) break;
                    var cntRaw = PromptOptional("Decrement count (Enter=1)") ?? "1";
                    if (!uint.TryParse(cntRaw, out var cnt)) cnt = 1;
                    var oid = PromptOptional("Joining Process Origin ID") ?? "";
                    js.JoiningProcessManagement.DecrementJoiningProcessCounter(uri, id, cnt, oid);
                    break;
                }
            case "26":
                {
                    var uri = Prompt("ProductInstance URI");
                    var id = Prompt("Joining Process ID");
                    var valRaw = Prompt("Counter value (UInt32)");
                    if (uri is null || id is null || valRaw is null) break;
                    if (!uint.TryParse(valRaw, out var val)) { _log.LogWarning("Invalid number."); break; }
                    var oid = PromptOptional("Joining Process Origin ID") ?? "";
                    js.JoiningProcessManagement.SetJoiningProcessCounter(uri, id, val, oid);
                    break;
                }
            case "27":
                {
                    var uri = Prompt("ProductInstance URI");
                    var id = Prompt("Joining Process ID");
                    var sizeRaw = Prompt("Max counter size (UInt32)");
                    if (uri is null || id is null || sizeRaw is null) break;
                    if (!uint.TryParse(sizeRaw, out var size)) { _log.LogWarning("Invalid number."); break; }
                    var oid = PromptOptional("Joining Process Origin ID") ?? "";
                    js.JoiningProcessManagement.SetJoiningProcessSize(uri, id, size, oid);
                    break;
                }

            // ── ASSET MANAGEMENT – EXTENDED ───────────────────────────────────
            case "28":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri is null) break;
                    var dtRaw = PromptOptional("DateTime ISO 8601 (Enter=UtcNow)") ?? "";
                    DateTime? dt = null;
                    if (!string.IsNullOrEmpty(dtRaw) && DateTime.TryParse(dtRaw, out var parsed))
                        dt = parsed.ToUniversalTime();
                    else if (!string.IsNullOrEmpty(dtRaw))
                    { _log.LogWarning("Could not parse date – using UtcNow."); }
                    js.AssetManagement.SetTime(uri, dt);
                    break;
                }
            case "29":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri is null) break;
                    var idsRaw = PromptOptional("Signal IDs (comma-sep, Enter=all)") ?? "";
                    var ids = string.IsNullOrEmpty(idsRaw)
                        ? null
                        : idsRaw.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
                    js.AssetManagement.GetIOSignals(uri, ids);
                    break;
                }
            case "30":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri is null) break;
                    var sigId = Prompt("Signal ID");
                    if (sigId is null) break;
                    var sigValRaw = Prompt("Signal value (numeric)");
                    if (sigValRaw is null) break;
                    if (!double.TryParse(sigValRaw, System.Globalization.NumberStyles.Any,
                            System.Globalization.CultureInfo.InvariantCulture, out var sigVal))
                    { _log.LogWarning("Invalid number."); break; }
                    var signal = new UAModel.IJTBase.SignalDataType { SignalId = sigId, SignalValue = new Opc.Ua.Variant(sigVal) };
                    js.AssetManagement.SetIOSignals(uri, [signal]);
                    break;
                }

            // ── SIMULATION ────────────────────────────────────────────────────
            case "31":
                {
                    Console.WriteLine("  Result types: 0=SIMPLE_OK  1=ONE_STEP_OK  2=MULTI_STEP_OK  3=NOK_FAILING  4=NOK_TRIGGER_LOST");
                    var tRaw = PromptOptional("Result type (Enter=0)") ?? "0";
                    if (!uint.TryParse(tRaw, out var rType)) rType = 0;
                    var traces = PromptBool("Include traces", defaultYes: false);
                    js.SimulationManagement.SimulateSingleResult(rType, traces);
                    break;
                }
            case "32":
                {
                    Console.WriteLine("  Classification: 2=SYNC  3=BATCH (default)");
                    var cRaw = PromptOptional("Classification (Enter=3)") ?? "3";
                    if (!byte.TryParse(cRaw, out var cls)) cls = 3;
                    var nRaw = PromptOptional("Number of child results (Enter=3)") ?? "3";
                    if (!uint.TryParse(nRaw, out var numCh)) numCh = 3;
                    var traces = PromptBool("Include traces", defaultYes: false);
                    var refs = PromptBool("Send as references", defaultYes: false);
                    js.SimulationManagement.SimulateBatchOrSyncResult(cls, numCh, traces, refs);
                    break;
                }
            case "33":
                {
                    var refs = PromptBool("Send child results as references", defaultYes: false);
                    js.SimulationManagement.SimulateJobResult(refs);
                    break;
                }
            case "34":
                {
                    Console.WriteLine("  Result types: 0=SIMPLE_OK  1=ONE_STEP_OK  2=MULTI_STEP_OK  3=NOK_FAILING  4=NOK_TRIGGER_LOST");
                    var tRaw = PromptOptional("Result type (Enter=0)") ?? "0";
                    if (!uint.TryParse(tRaw, out var rType)) rType = 0;
                    var traces = PromptBool("Include traces", defaultYes: false);
                    var fromRaw = PromptOptional("From sequence number (Enter=1)") ?? "1";
                    if (!ulong.TryParse(fromRaw, out var fromSeq)) fromSeq = 1;
                    var toRaw = PromptOptional($"To sequence number (Enter={fromSeq + 9}, min=fromSeq+5)") ?? $"{fromSeq + 9}";
                    if (!ulong.TryParse(toRaw, out var toSeq)) toSeq = fromSeq + 9;
                    var msRaw = PromptOptional("Min delay between results ms (Enter=500, min=100)") ?? "500";
                    if (!long.TryParse(msRaw, out var ms)) ms = 500;
                    var upd = PromptBool("Update result variables", defaultYes: true);
                    js.SimulationManagement.SimulateBulkResults(rType, traces, fromSeq, toSeq, ms, upd);
                    break;
                }
            case "35":
                {
                    Console.WriteLine("  Event types (sample): 1=TOOL_CONNECTED  6=TOOL_STARTED  13=TOOL_ERROR  29=PROGRAM_SELECTED  31=EXECUTION_STARTED  38=RECEIVED_IDENTIFIER");
                    var eRaw = PromptOptional("Event type 1-60 (Enter=1)") ?? "1";
                    if (!uint.TryParse(eRaw, out var eType) || eType < 1 || eType > 60) eType = 1;
                    js.SimulationManagement.SimulateEvent(eType);
                    break;
                }
            case "36":
                {
                    Console.WriteLine("  Event types (sample): 1=TOOL_CONNECTED  6=TOOL_STARTED  13=TOOL_ERROR  29=PROGRAM_SELECTED  31=EXECUTION_STARTED  38=RECEIVED_IDENTIFIER");
                    var eRaw = PromptOptional("Event type 1-60 (Enter=1)") ?? "1";
                    if (!uint.TryParse(eRaw, out var eType) || eType < 1 || eType > 60) eType = 1;
                    var cntRaw = PromptOptional("Count 1-1000 (Enter=10)") ?? "10";
                    if (!uint.TryParse(cntRaw, out var eCnt) || eCnt < 1 || eCnt > 1000) eCnt = 10;
                    js.SimulationManagement.SimulateBulkEvents(eType, eCnt);
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
    lock (IJT_CSharp_Client.Helpers.IjtLog.ConsoleLock) { Console.Write($"  {label}: "); }
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
    lock (IJT_CSharp_Client.Helpers.IjtLog.ConsoleLock) { Console.Write($"  {label} (optional, Enter to skip): "); }
    var v = Console.ReadLine()?.Trim();
    if (string.IsNullOrWhiteSpace(v)) return "";
    if (v.Length > maxLen) { Console.WriteLine($"  Input too long (max {maxLen} chars) - cancelled."); return null; }
    return v;
}

/// <summary>
/// Prompts a Y/N question on the console, protected by ConsoleLock.
/// Returns true when the user presses Y (or defaultYes=true + blank entry),
/// false when the user presses N (or defaultYes=false + blank entry).
/// </summary>
static bool PromptBool(string question, bool defaultYes = false)
{
    var hint = defaultYes ? "[Y/n]" : "[y/N]";
    lock (IJT_CSharp_Client.Helpers.IjtLog.ConsoleLock) { Console.Write($"  {question}? {hint}: "); }
    var raw = (Console.ReadLine() ?? "").Trim();
    if (string.IsNullOrEmpty(raw)) return defaultYes;
    return raw.Equals("y", StringComparison.OrdinalIgnoreCase);
}

static void PrintBanner()
{
    Console.WriteLine();
    Console.WriteLine("  +--------------------------------------------------+");
    Console.WriteLine("  |   IJT OPC UA Client  -  C# Reference Example    |");
    Console.WriteLine("  |   OPC UA for Industrial Joining Technologies     |");
    Console.WriteLine("  +--------------------------------------------------+");
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
  +---------------------------------------------------------+
  | SUBSCRIPTIONS (toggle: press number to start/stop)     |
  |  1  IJT events          ResultReady + SystemEvents [{ev}] |
  |  2  Result variable     ResultManagement/Results   [{rv}] |
  |  3  Asset variables     AssetManagement/Assets     [{av}] |
  |                                                         |
  | RESULT MANAGEMENT                                       |
  |  4  GetLatestResult                        > log        |
  |  5  GetResultById                          > log        |
  |                                                         |
  | ASSET MANAGEMENT                                        |
  |  6  EnableAsset                                         |
  |  7  SendTextIdentifiers                                 |
  |  8  SendIdentifiers (EntityDataType)                    |
  |  9  GetIdentifiers                         > log        |
  | 10  ResetIdentifiers                                    |
  |                                                         |
  | JOINING PROCESS MANAGEMENT                              |
  | 11  GetJoiningProcessList                  > log        |
  | 12  SelectJoiningProcess                                |
  | 13  GetSelectedJoiningProgram              > log        |
  |                                                         |
  | JOINT MANAGEMENT                                        |
  | 14  GetJointList                           > log        |
  | 15  GetJoint                               > log        |
  | 16  SelectJoint                                         |
  | 17  DeleteJoint                                         |
  | 18  SendJoint                                           |
  |                                                         |
  | JOINING PROCESS MANAGEMENT - EXTENDED                   |
  | 19  StartSelectedJoining          (fires result)        |
  | 20  StartJoiningProcess                                 |
  | 21  AbortJoiningProcess                                 |
  | 22  DeselectJoiningProcess                              |
  | 23  ResetJoiningProcess                                 |
  | 24  IncrementJoiningProcessCounter                      |
  | 25  DecrementJoiningProcessCounter                      |
  | 26  SetJoiningProcessCounter                            |
  | 27  SetJoiningProcessSize                               |
  |                                                         |
  | ASSET MANAGEMENT - EXTENDED                             |
  | 28  SetTime                                             |
  | 29  GetIOSignals                           > log        |
  | 30  SetIOSignals                           > log        |
  |                                                         |
  | SIMULATION                                              |
  | 31  SimulateSingleResult          (fires result)        |
  | 32  SimulateBatchOrSyncResult     (fires result)        |
  | 33  SimulateJobResult             (fires result)        |
  | 34  SimulateBulkResults           (fires results)       |
  | 35  SimulateEvent                 (fires event)         |
  | 36  SimulateBulkEvents            (fires events)        |
  |                                                         |
  |  0  Quit            m / Enter = redraw this menu       |
  +---------------------------------------------------------+
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
                "Events arrive asynchronously and are logged to logs/result/ and logs/events/.",
                [],
                ["Event notifications (ResultReady / JoiningSystemEvent)"]);
            break;
        case "2":
            IjtMenuHelper.PrintUsage(
                "Toggle Result Variable",
                "Subscribes or unsubscribes a data-change notification on " +
                "ResultManagement/Results/Result. Fires whenever a new result is written to the node.",
                [],
                ["Data-change notification > logs/result/result.json"]);
            break;
        case "3":
            IjtMenuHelper.PrintUsage(
                "Toggle Asset Variables",
                "Subscribes or unsubscribes data-change notifications on ALL variables " +
                "recursively under every asset instance object in " +
                "AssetManagement/Assets/Controllers/*, .../Tools/*, etc. " +
                "Each asset snapshot is flushed to logs/assets/<Category>_<Name>.json " +
                "whenever any of its subscribed variables changes.",
                [],
                ["logs/assets/<Category>_<Name>.json per asset"]);
            break;
        // RESULT MANAGEMENT
        case "4":
            IjtMenuHelper.PrintUsage(
                "GetLatestResult",
                "Calls ResultManagement/MethodSet/GetLatestResult. " +
                "Full result logged to: logs/result/result.json",
                ["TimeoutMs: Int32 (default 5000)"],
                ["ResultHandle", "Result > logs/result/result.json", "Error"]);
            break;
        case "5":
            IjtMenuHelper.PrintUsage(
                "GetResultById",
                "Calls ResultManagement/MethodSet/GetResultById. " +
                "Full result logged to: logs/result/result.json",
                ["ResultId: String", "TimeoutMs: Int32 (default 5000)"],
                ["ResultHandle", "Result > logs/result/result.json", "Error"]);
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
                "Full entity list logged to: logs/entity_list/entity_list.json",
                ["ProductInstanceUri: String", "IdentifierNames: String[] (empty = return all)"],
                ["EntityList > logs/entity_list/entity_list.json", "Status", "StatusMessage"]);
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
                "Full list logged to: logs/joining_process/joining_process_list.json",
                ["ProductInstanceUri: String (optional)"],
                ["JoiningProcessList > logs/joining_process/joining_process_list.json", "Status", "StatusMessage"]);
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
        // JOINING PROCESS MANAGEMENT – EXTENDED
        case "19":
            IjtMenuHelper.PrintUsage(
                "StartSelectedJoining",
                "Calls JoiningProcessManagement/StartSelectedJoining. " +
                "REAL: fires a tightening result based on the currently selected joint's program. " +
                "Prerequisite: call SelectJoint (cmd 16) first to set the active joint/program.",
                ["ProductInstanceUri: String (Tool URI)", "DeselectAfterJoining: Boolean [y/N]"],
                ["Status", "StatusMessage"]);
            break;
        case "20":
            IjtMenuHelper.PrintUsage(
                "StartJoiningProcess",
                "Calls JoiningProcessManagement/StartJoiningProcess. " +
                "Stub on simulator: logs inputs, returns OK. " +
                "Key entity: PROGRAM (EntityType=27, IsExternal=false, EntityId=JoiningProcessId). " +
                "Optional VIN entity: VEHICLE (EntityType=20, IsExternal=true, EntityId=VIN number).",
                [
                    "ProductInstanceUri: String (Tool URI)",
                    "JoiningProcessId: String (e.g. 0952E9B4-05F6-4B43-B66C-B8027FBE966A)",
                    "JoiningProcessOriginId: String (optional)",
                    "VIN: String (optional, added as VEHICLE entity)",
                ],
                ["Status", "StatusMessage"]);
            break;
        case "21":
            IjtMenuHelper.PrintUsage(
                "AbortJoiningProcess",
                "Calls JoiningProcessManagement/AbortJoiningProcess. " +
                "Stub on simulator: logs inputs, returns OK.",
                ["ProductInstanceUri: String", "JoiningProcessId: String", "JoiningProcessOriginId: String (optional)", "AbortMessage: String (optional)"],
                ["Status", "StatusMessage"]);
            break;
        case "22":
            IjtMenuHelper.PrintUsage(
                "DeselectJoiningProcess",
                "Calls JoiningProcessManagement/DeselectJoiningProcess. " +
                "Stub on simulator: logs ProductInstanceUri, returns OK.",
                ["ProductInstanceUri: String (optional)"],
                ["Status", "StatusMessage"]);
            break;
        case "23":
            IjtMenuHelper.PrintUsage(
                "ResetJoiningProcess",
                "Calls JoiningProcessManagement/ResetJoiningProcess. " +
                "Stub on simulator: logs inputs, returns OK.",
                ["ProductInstanceUri: String", "JoiningProcessId: String", "JoiningProcessOriginId: String (optional)"],
                ["Status", "StatusMessage"]);
            break;
        case "24":
            IjtMenuHelper.PrintUsage(
                "IncrementJoiningProcessCounter",
                "Calls JoiningProcessManagement/IncrementJoiningProcessCounter. " +
                "Stub on simulator: logs inputs, returns OK.",
                ["ProductInstanceUri: String", "JoiningProcessId: String", "IncrementCount: UInt32 (default 1)", "JoiningProcessOriginId: String (optional)"],
                ["Status", "StatusMessage"]);
            break;
        case "25":
            IjtMenuHelper.PrintUsage(
                "DecrementJoiningProcessCounter",
                "Calls JoiningProcessManagement/DecrementJoiningProcessCounter. " +
                "Stub on simulator: logs inputs, returns OK.",
                ["ProductInstanceUri: String", "JoiningProcessId: String", "DecrementCount: UInt32 (default 1)", "JoiningProcessOriginId: String (optional)"],
                ["Status", "StatusMessage"]);
            break;
        case "26":
            IjtMenuHelper.PrintUsage(
                "SetJoiningProcessCounter",
                "Calls JoiningProcessManagement/SetJoiningProcessCounter. " +
                "Stub on simulator: logs inputs, returns OK.",
                ["ProductInstanceUri: String", "JoiningProcessId: String", "CounterValue: UInt32", "JoiningProcessOriginId: String (optional)"],
                ["Status", "StatusMessage"]);
            break;
        case "27":
            IjtMenuHelper.PrintUsage(
                "SetJoiningProcessSize",
                "Calls JoiningProcessManagement/SetJoiningProcessSize. " +
                "Stub on simulator: logs inputs, returns OK.",
                ["ProductInstanceUri: String", "JoiningProcessId: String", "MaxCounterSize: UInt32", "JoiningProcessOriginId: String (optional)"],
                ["Status", "StatusMessage"]);
            break;
        // ASSET MANAGEMENT – EXTENDED
        case "28":
            IjtMenuHelper.PrintUsage(
                "SetTime",
                "Calls AssetManagement/MethodSet/SetTime. " +
                "Stub on simulator: logs ProductInstanceUri + DateTime, returns OK. " +
                "Leave DateTime blank to use server UtcNow.",
                ["ProductInstanceUri: String", "DateTime: ISO-8601 string (optional, default = UtcNow)"],
                ["Status", "StatusMessage"]);
            break;
        case "29":
            IjtMenuHelper.PrintUsage(
                "GetIOSignals",
                "Calls AssetManagement/MethodSet/GetIOSignals. " +
                "REAL: simulator returns up to 500 dummy SignalDataType entries. " +
                "Full signal list logged to: logs/io_signals/io_signals.json",
                ["ProductInstanceUri: String", "SignalIds: String[] (comma-sep, empty = return all)"],
                ["SignalList > logs/io_signals/io_signals.json", "Status", "StatusMessage"]);
            break;
        case "30":
            IjtMenuHelper.PrintUsage(
                "SetIOSignals",
                "Calls AssetManagement/MethodSet/SetIOSignals. " +
                "Stub on simulator: parses signals, logs each, returns per-signal status 0. " +
                "Per-signal statuses logged to: logs/io_signals/io_signals.json",
                ["ProductInstanceUri: String", "SignalId: String", "SignalValue: Double"],
                ["PerSignalStatuses > logs/io_signals/io_signals.json", "Status", "StatusMessage"]);
            break;
        // SIMULATION
        case "31":
            IjtMenuHelper.PrintUsage(
                "SimulateSingleResult",
                "Calls Simulations/SimulateResults/SimulateSingleResult. " +
                "REAL: fires one result + ResultReady event immediately. " +
                "Result arrives via subscription (cmd 1 or 2). " +
                "Types: 0=SIMPLE_OK 1=ONE_STEP_OK 2=MULTI_STEP_OK 3=NOK_FAILING 4=NOK_TRIGGER_LOST.",
                ["ResultType: UInt32 (0-4, default 0)", "IncludeTraces: Boolean [y/N]"],
                ["(result fired as async event)"]);
            break;
        case "32":
            IjtMenuHelper.PrintUsage(
                "SimulateBatchOrSyncResult",
                "Calls Simulations/SimulateResults/SimulateBatch_Or_Sync_Result. " +
                "REAL: fires a batch (3) or sync (2) result with child results. " +
                "Result arrives via subscription (cmd 1 or 2).",
                ["Classification: Byte 2=SYNC 3=BATCH (default 3)", "NumChildren: UInt32 (default 3)", "IncludeTraces: Boolean [y/N]", "SendAsReferences: Boolean [y/N]"],
                ["(result fired as async event)"]);
            break;
        case "33":
            IjtMenuHelper.PrintUsage(
                "SimulateJobResult",
                "Calls Simulations/SimulateResults/SimulateJobResult. " +
                "REAL: fires a job result containing multiple child results. " +
                "Result arrives via subscription (cmd 1 or 2).",
                ["SendAsReferences: Boolean [y/N]"],
                ["(result fired as async event)"]);
            break;
        case "34":
            IjtMenuHelper.PrintUsage(
                "SimulateBulkResults",
                "Calls Simulations/SimulateResults/SimulateBulkResults. " +
                "REAL: fires many results in a server background thread over a sequence range. " +
                "Constraint: toSeq >= fromSeq+5 and minDurationMs >= 100.",
                ["ResultType: UInt32 (0-4)", "IncludeTraces: Boolean [y/N]", "FromSeq: UInt64 (default 1)", "ToSeq: UInt64 (default fromSeq+9)", "MinDurationMs: Int64 >= 100 (default 500)", "UpdateResultVariables: Boolean [Y/n]"],
                ["(results fired as async events)"]);
            break;
        case "35":
            IjtMenuHelper.PrintUsage(
                "SimulateEvent",
                "Calls Simulations/SimulateEventsAndConditions/SimulateEvents. " +
                "REAL: fires exactly 1 JoiningSystemEvent of the given type. " +
                "Event arrives via subscription (cmd 1). " +
                "Sample types: 1=TOOL_CONNECTED 6=TOOL_STARTED 13=TOOL_ERROR 29=PROGRAM_SELECTED 31=EXECUTION_STARTED 38=RECEIVED_IDENTIFIER.",
                ["EventType: UInt32 (1-60, default 1)"],
                ["(event fired as async event)"]);
            break;
        case "36":
            IjtMenuHelper.PrintUsage(
                "SimulateBulkEvents",
                "Calls Simulations/SimulateEventsAndConditions/SimulateBulkEvents. " +
                "REAL: fires up to 1000 JoiningSystemEvents of the given type. " +
                "Events arrive via subscription (cmd 1). Maximum count = 1000.",
                ["EventType: UInt32 (1-60, default 1)", "Count: UInt32 (1-1000, default 10)"],
                ["(events fired as async events)"]);
            break;
        default:
            Console.WriteLine($"  Unknown command '{cmd}'. Valid commands: 0-36, m, h.");
            break;
    }
}
