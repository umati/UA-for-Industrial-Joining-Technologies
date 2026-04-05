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

IjtSession? session;
try
{
    _log.LogInformation("Connecting to {Url} …", config.ServerUrl);
    session = await IjtSession.ConnectAsync(config, cts.Token);
}
catch (Opc.Ua.ServiceResultException srex)
{
    _log.LogError("Connection failed [{Status}]: {Msg}", srex.StatusCode, srex.Message);
    IjtLog.Shutdown(); return 1;
}
catch (Exception ex)
{
    _log.LogError(ex, "Connection failed");
    IjtLog.Shutdown(); return 1;
}

await using (session)
{
    using var resultMgmt = new ResultManagement(session);
    using var assetMgmt = new AssetManagement(session);
    using var jpm = new JoiningProcessManagement(session);
    using var eventSub = new EventSubscriber(session);

    // ── Wire up event handlers ─────────────────────────────────────────────────
    eventSub.OnResultReady += (_, e) =>
    {
        // One-liner to logger
        _log.LogInformation("Result received | {Name} | Seq#{Seq} | {Class} | {Time:HH:mm:ss}",
            e.Name ?? e.ResultId, e.SequenceNumber, e.Classification, e.EventTime);
        _log.LogInformation("Result logged to: {Path}", IjtFileLogger.ResultLogPath);

        // Full detail to log file (use full ResultDataType when available, fall back to event fields)
        var text = e.Result is not null
            ? IjtResultFormatter.FormatResult(e.Result, e.EventTime)
            : IjtResultFormatter.FormatResultEventFields(
                e.ResultId, e.Classification, e.Name, e.SequenceNumber, e.AssemblyType, e.EventTime);
        IjtFileLogger.WriteResult(text);
    };

    eventSub.OnJoiningSystemEvent += (_, e) =>
    {
        // One-liner to logger
        _log.LogInformation("System event | Code:{Code} | {Text} | {Time:HH:mm:ss}",
            e.EventCode, e.EventText, e.EventTime);
        _log.LogInformation("Event logged to: {Path}", IjtFileLogger.EventLogPath);

        // Full detail to log file
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

        switch (cmd)
        {
            // Events
            case "1":
                eventSub.Subscribe();
                _subscribed = true;
                _log.LogInformation("Subscribed to result and system events.");
                _log.LogInformation("Result log: {P}", IjtFileLogger.ResultLogPath);
                _log.LogInformation("Event  log: {P}", IjtFileLogger.EventLogPath);
                break;
            case "2":
                eventSub.Unsubscribe();
                _subscribed = false;
                break;

            // Results
            case "3":
                resultMgmt.GetLatestResult();
                break;
            case "4":
                {
                    var rid = Prompt("Result ID");
                    if (rid != null) resultMgmt.GetResultById(rid);
                    break;
                }
            case "5":
                resultMgmt.SubscribeResultVariable();
                break;

            // Asset Management
            case "6":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri is null) break;
                    Console.Write("  Enable? [Y/n]: ");
                    var ynRaw = (Console.ReadLine() ?? "y").Trim();
                    // Reject pathologically long input; default to enable
                    var yn = ynRaw.Length > 10 ? "y" : ynRaw;
                    assetMgmt.EnableAsset(uri, !yn.Equals("n", StringComparison.OrdinalIgnoreCase));
                    break;
                }
            case "7":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri != null) assetMgmt.SendTextIdentifiers(uri, ["ID-001", "Batch-2024"]);
                    break;
                }
            case "8":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri != null) assetMgmt.GetIdentifiers(uri);
                    break;
                }
            case "9":
                {
                    var uri = Prompt("ProductInstance URI");
                    if (uri != null) assetMgmt.ResetIdentifiers(uri);
                    break;
                }
            case "10":
                assetMgmt.SubscribeAssetVariables();
                break;

            // Joining Process
            case "11":
                jpm.GetJoiningProcessList();
                break;
            case "12":
                {
                    var id = Prompt("Joining Process ID");
                    if (id is null) break;
                    var name = Prompt("Selection name (optional, press Enter to skip)") ?? "";
                    jpm.SelectJoiningProcess(id, selectionName: name);
                    break;
                }
            case "13":
                jpm.GetSelectedJoiningProgram();
                break;

            // Identifiers demo
            case "14":
                {
                    var entities = new List<UAModel.IJTBase.EntityDataType>
                {
                    new() { Name = "Batch-A", EntityId = "ENT-001", IsExternal = false, EntityType = 0 }
                };
                    assetMgmt.SendIdentifiers(entities);
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
  │   3  Get latest result                            │
  │   4  Get result by ID                             │
  │   5  Subscribe result variable                    │
  │                                                   │
  │  ASSET MANAGEMENT                                 │
  │   6  Enable / disable asset                       │
  │   7  Send text identifiers (demo)                 │
  │   8  Get identifiers                              │
  │   9  Reset identifiers                            │
  │  10  Subscribe asset variables                    │
  │                                                   │
  │  JOINING PROCESS                                  │
  │  11  Get joining process list                     │
  │  12  Select joining process                       │
  │  13  Get selected joining program                 │
  │  14  Send identifiers (EntityDataType demo)       │
  │                                                   │
  │   0  Quit                                         │
  └──────────────────────────────────────────────────┘
  """);
    Console.Write("  Command: ");
}
