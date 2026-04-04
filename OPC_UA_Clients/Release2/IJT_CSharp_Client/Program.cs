#nullable enable

using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Configuration;

// ── Cancellation ──────────────────────────────────────────────────────────────
using var cts = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) => { e.Cancel = true; cts.Cancel(); };

Console.WriteLine("╔══════════════════════════════════════════════════╗");
Console.WriteLine("║   IJT C# Client — OPC UA IJT Companion Spec     ║");
Console.WriteLine("╚══════════════════════════════════════════════════╝");

// ── Configuration ─────────────────────────────────────────────────────────────
var config = ClientConfig.FromEnvironment();
Console.WriteLine($"  Server: {config.ServerUrl}");

// ── Connect ───────────────────────────────────────────────────────────────────
IjtSession? session;
try
{
    session = await IjtSession.ConnectAsync(config, cts.Token);
}
catch (Exception ex)
{
    Console.WriteLine($"  ✗ Connection failed: {ex.Message}");
    return 1;
}

// ── Main interaction ──────────────────────────────────────────────────────────
await using (session)
{
    var resultMgmt = new ResultManagement(session);
    var assetMgmt  = new AssetManagement(session);
    var jpm        = new JoiningProcessManagement(session);
    var eventSub   = new EventSubscriber(session);

    // Hook event subscriber to print results
    eventSub.OnResultReady += (_, e) =>
    {
        Console.WriteLine(
            $"\n  [EVENT] ResultReady | Id={e.ResultId} | " +
            $"Status={e.OverallStatus} | Time={e.EventTime:HH:mm:ss}");
    };
    eventSub.OnJoiningSystemEvent += (_, e) =>
    {
        Console.WriteLine(
            $"\n  [EVENT] JoiningSystem | Code={e.EventCode} | {e.EventText}");
    };

    // ── Main menu loop ────────────────────────────────────────────────────────
    while (!cts.Token.IsCancellationRequested)
    {
        PrintMenu();

        ConsoleKeyInfo keyInfo;
        try { keyInfo = Console.ReadKey(intercept: true); }
        catch (InvalidOperationException) { break; } // stdin redirected (non-interactive)

        switch (char.ToLowerInvariant(keyInfo.KeyChar))
        {
            // ── Event subscriptions ────────────────────────────────────────────
            case '1':
                eventSub.Subscribe();
                break;

            case '2':
                eventSub.Unsubscribe();
                break;

            // ── Result Management ─────────────────────────────────────────────
            case '3':
                resultMgmt.GetLatestResult();
                break;

            case '4':
                Console.Write("\n  Enter ResultId: ");
                var rid = Console.ReadLine() ?? "";
                resultMgmt.GetResultById(rid);
                break;

            case '5':
                resultMgmt.SubscribeResultVariable();
                break;

            // ── Asset Management ──────────────────────────────────────────────
            case '6':
                Console.Write("\n  Enter ProductInstanceUri: ");
                var uri = Console.ReadLine() ?? "";
                Console.Write("  Enable? (y/n): ");
                var en = (Console.ReadLine() ?? "y").Trim().ToLowerInvariant() == "y";
                assetMgmt.EnableAsset(uri, en);
                break;

            case '7':
                Console.Write("\n  Enter ProductInstanceUri: ");
                var piUri = Console.ReadLine() ?? "";
                assetMgmt.SendTextIdentifiers(piUri, ["ID-001", "Batch-2024"]);
                break;

            case '8':
                Console.Write("\n  Enter ProductInstanceUri for GetIdentifiers: ");
                var piUri2 = Console.ReadLine() ?? "";
                assetMgmt.GetIdentifiers(piUri2);
                break;

            case '9':
                Console.Write("\n  Enter ProductInstanceUri for ResetIdentifiers: ");
                var piUri3 = Console.ReadLine() ?? "";
                assetMgmt.ResetIdentifiers(piUri3);
                break;

            case 'a':
                assetMgmt.SubscribeAssetVariables();
                break;

            // ── Joining Process Management ────────────────────────────────────
            case 'b':
                jpm.GetJoiningProcessList();
                break;

            case 'c':
                Console.Write("\n  Enter JoiningProcessId: ");
                var jpId = Console.ReadLine() ?? "";
                Console.Write("  SelectionName (optional): ");
                var snm = Console.ReadLine() ?? "";
                jpm.SelectJoiningProcess(jpId, selectionName: snm);
                break;

            case 'd':
                jpm.GetSelectedJoiningProgram();
                break;

            // ── SendIdentifiers demo ──────────────────────────────────────────
            case 'e':
                Console.Write("\n  Enter ProductInstanceUri: ");
                var piUri4 = Console.ReadLine() ?? "";
                _ = piUri4; // ProductInstanceUri not used by SendIdentifiers directly
                var entities = new List<UAModel.IJTBase.EntityDataType>
                {
                    new UAModel.IJTBase.EntityDataType
                    {
                        Name          = "Batch-A",
                        Description   = "Production batch A",
                        EntityId      = "ENT-001",
                        EntityOriginId = "",
                        IsExternal    = false,
                        EntityType    = 0,
                    }
                };
                assetMgmt.SendIdentifiers(entities);
                break;

            case 'q':
                cts.Cancel();
                break;

            default:
                // Unknown key — just re-display menu
                break;
        }
    }
}

Console.WriteLine("\n  Disconnected. Goodbye.");
return 0;

// ── Menu ──────────────────────────────────────────────────────────────────────
static void PrintMenu()
{
    Console.WriteLine(@"
┌─────────────────────────────────────────────────────────┐
│  Events                                                  │
│  [1] Subscribe to Result + JoiningSystem Events          │
│  [2] Unsubscribe from Events                             │
│  Result Management                                       │
│  [3] GetLatestResult                                     │
│  [4] GetResultById                                       │
│  [5] Subscribe ResultVariable                            │
│  Asset Management                                        │
│  [6] EnableAsset                                         │
│  [7] SendTextIdentifiers (demo)                          │
│  [8] GetIdentifiers                                      │
│  [9] ResetIdentifiers                                    │
│  [A] Subscribe Asset Variables (Controller/Tool)         │
│  Joining Process Management                              │
│  [B] GetJoiningProcessList                               │
│  [C] SelectJoiningProcess                                │
│  [D] GetSelectedJoiningProgram                           │
│  SendIdentifiers                                         │
│  [E] SendIdentifiers (EntityDataType demo)               │
│  [Q] Quit                                                │
└─────────────────────────────────────────────────────────┘
  Choice: ");
}
