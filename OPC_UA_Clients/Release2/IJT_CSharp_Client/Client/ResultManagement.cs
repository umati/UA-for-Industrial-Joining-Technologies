#nullable enable

using Opc.Ua;
using Opc.Ua.Client;
using IJT_CSharp_Client.Helpers;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// OPC UA IJT Result Management operations:
/// <list type="bullet">
///   <item>GetLatestResult  — retrieve the most recent tightening result</item>
///   <item>GetResultById    — retrieve a specific result by its ResultId</item>
///   <item>SubscribeResultVariable — monitor the live result variable via data-change subscription</item>
/// </list>
/// </summary>
public sealed class ResultManagement
{
    private readonly IjtSession _s;
    private Subscription?       _resultVarSubscription;

    /// <summary>Creates a new ResultManagement facade backed by <paramref name="ijtSession"/>.</summary>
    public ResultManagement(IjtSession ijtSession) => _s = ijtSession;

    // ── Node lookup ───────────────────────────────────────────────────────────

    /// <summary>
    /// Finds the ResultManagement object node: browses the JoiningSystem instance
    /// for a "ResultManagement" child; falls back to the type-level object NodeId.
    /// </summary>
    private NodeId GetResultManagementNode()
    {
        var child = _s.BrowseChild(_s.JoiningSystemNodeId, "ResultManagement");
        if (!child.IsNullNodeId) return child;

        // Fallback: type-definition node (most servers honour this for method calls)
        return _s.IjtBaseObjectId(UAModel.IJTBase.Objects.JoiningSystemType_ResultManagement);
    }

    // ── GetLatestResult ───────────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>ResultManagement/GetLatestResult</c> (method NodeId 7001).
    /// Output: [ResultHandle (uint32), Result (ExtensionObject)].
    /// </summary>
    public void GetLatestResult()
    {
        Console.WriteLine("\n── GetLatestResult ──────────────────────────────────");

        var objectId = GetResultManagementNode();
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            Console.WriteLine("  ✗ ResultManagement node or method not found.");
            return;
        }

        try
        {
            var outputs = _s.CallMethod(objectId, methodId);
            PrintResultOutputs(outputs);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"  ✗ GetLatestResult error: {ex.Message}");
        }
    }

    // ── GetResultById ─────────────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>ResultManagement/GetResultById</c> (method NodeId 7002).
    /// Input: ResultId (string). Output: [ResultHandle (uint32), Result (ExtensionObject)].
    /// </summary>
    public void GetResultById(string resultId)
    {
        Console.WriteLine($"\n── GetResultById (id={resultId}) ──────────────────────");

        var objectId = GetResultManagementNode();
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetResultById);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            Console.WriteLine("  ✗ ResultManagement node or method not found.");
            return;
        }

        try
        {
            var outputs = _s.CallMethod(objectId, methodId, resultId);
            PrintResultOutputs(outputs);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"  ✗ GetResultById error: {ex.Message}");
        }
    }

    // ── Subscribe to ResultVariable ───────────────────────────────────────────

    /// <summary>
    /// Creates a data-change subscription on the Result variable under
    /// <c>ResultManagement/Results</c>. Prints notifications to console.
    /// Does nothing if already subscribed.
    /// </summary>
    public void SubscribeResultVariable()
    {
        if (_resultVarSubscription != null)
        {
            Console.WriteLine("  ⚠ Result variable subscription already active.");
            return;
        }

        Console.WriteLine("\n── Subscribing to Result variable ───────────────────");

        var rmNode = GetResultManagementNode();

        // Try to find the Results folder child, then the first variable inside
        var resultsFolder = _s.BrowseChild(rmNode, "Results");
        NodeId resultVarNode = NodeId.Null;

        if (!resultsFolder.IsNullNodeId)
        {
            // Find first variable child of Results
            _s.Session.Browse(null, null, resultsFolder, 0,
                BrowseDirection.Forward, ReferenceTypeIds.HierarchicalReferences,
                true, (uint)NodeClass.Variable, out _, out var varRefs);
            if (varRefs?.Count > 0)
                resultVarNode = (NodeId)varRefs[0].NodeId;
        }

        if (resultVarNode.IsNullNodeId)
        {
            Console.WriteLine("  ✗ Result variable node not found — skipping subscription.");
            return;
        }

        _resultVarSubscription = new Subscription(_s.Session.DefaultSubscription)
        {
            DisplayName        = "IJT ResultVariable",
            PublishingInterval = _s.Config.PublishingIntervalMs,
        };

        var item = new MonitoredItem(_resultVarSubscription.DefaultItem)
        {
            DisplayName      = "ResultVariable",
            StartNodeId      = resultVarNode,
            AttributeId      = Attributes.Value,
            SamplingInterval = 500,
        };
        item.Notification += OnResultVariableChanged;

        _resultVarSubscription.AddItem(item);
        _s.Session.AddSubscription(_resultVarSubscription);
        _resultVarSubscription.Create();

        Console.WriteLine($"  ✓ Subscribed to Result variable ({resultVarNode}).");
    }

    private static void OnResultVariableChanged(MonitoredItem item, MonitoredItemNotificationEventArgs e)
    {
        foreach (var value in item.DequeueValues())
        {
            Console.WriteLine($"  [DATA] ResultVariable @ {DateTime.Now:HH:mm:ss.fff}  Status={value.StatusCode}");
            if (value.Value != null)
                Console.WriteLine($"    Value: {ExtensionObjectHelper.FormatVariantValue(value.Value)}");
        }
    }

    /// <summary>Stops the result variable data-change subscription if active.</summary>
    public void StopResultVariableSubscription()
    {
        if (_resultVarSubscription == null) return;
        try
        {
            _resultVarSubscription.Delete(silent: true);
            _s.Session.RemoveSubscription(_resultVarSubscription);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"  ⚠ Subscription stop warning: {ex.Message}");
        }
        finally
        {
            _resultVarSubscription = null;
            Console.WriteLine("  ✓ Result variable subscription stopped.");
        }
    }

    // ── Output formatting ─────────────────────────────────────────────────────

    private static void PrintResultOutputs(IList<object> outputs)
    {
        if (outputs.Count == 0) { Console.WriteLine("  [DATA] No output returned."); return; }
        ExtensionObjectHelper.PrintOutputArguments(outputs);
    }
}
