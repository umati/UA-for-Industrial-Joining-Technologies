#nullable enable

using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;
using Opc.Ua;
using Opc.Ua.Client;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// OPC UA IJT Result Management operations:
/// <list type="bullet">
///   <item>GetLatestResult  — retrieve the most recent tightening result</item>
///   <item>GetResultById    — retrieve a specific result by its ResultId</item>
///   <item>SubscribeResultVariable — monitor the live result variable via data-change subscription</item>
/// </list>
/// </summary>
public sealed class ResultManagement : IDisposable
{
    private readonly ILogger<ResultManagement> _log = IjtLog.For<ResultManagement>();
    private readonly IJoiningSystem _js;
    private Subscription? _resultVarSubscription;
    private NodeId? _rmNodeId;

    /// <summary>Creates a new ResultManagement facade backed by <paramref name="js"/>.</summary>
    public ResultManagement(IJoiningSystem js) => _js = js;

    /// <summary>True when the Result variable data-change subscription is active.</summary>
    public bool IsResultVarSubscribed => _resultVarSubscription != null;

    /// <summary>Clears the cached ResultManagement node reference so the next operation re-browses the address space.</summary>
    public void InvalidateNodeCache() => _rmNodeId = null;

    // ── Node lookup ───────────────────────────────────────────────────────────

    /// <summary>
    /// Finds the ResultManagement object node: browses the JoiningSystem instance
    /// for a "ResultManagement" child; falls back to the type-level object NodeId.
    /// Result is cached until <see cref="InvalidateNodeCache"/> is called.
    /// </summary>
    private NodeId GetResultManagementNode()
    {
        if (_rmNodeId is not null && !_rmNodeId.IsNullNodeId)
            return _rmNodeId;

        var child = _js.BrowseChild(_js.NodeId, UAModel.MachineryResult.BrowseNames.ResultManagement);
        if (!child.IsNullNodeId)
        {
            _rmNodeId = child;
            return _rmNodeId;
        }

        // Fallback: type-definition node (most servers honour this for method calls)
        var fallback = _js.IjtBaseObjectId(UAModel.IJTBase.Objects.JoiningSystemType_ResultManagement);
        if (!fallback.IsNullNodeId)
            _log.LogWarning("⚠ ResultManagement fallback to type NodeId.");
        _rmNodeId = fallback;
        return _rmNodeId;
    }

    // ── GetLatestResult ───────────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>ResultManagement/GetLatestResult</c> (method NodeId 7001).
    /// Output: [ResultHandle (uint32), Result (ExtensionObject), Error (int32)].
    /// </summary>
    /// <param name="timeoutMs">Timeout hint for the server in milliseconds (default 5000). Pass 0 for no estimate.</param>
    public void GetLatestResult(int timeoutMs = 5000)
    {
        _log.LogInformation("\n── GetLatestResult ──────────────────────────────────");

        var objectId = GetResultManagementNode();
        var methodId = _js.BrowseMethod(objectId, "GetLatestResult",
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("✗ ResultManagement node or method not found.");
            return;
        }

        try
        {
            var outputs = _js.CallMethod(objectId, methodId, (int)timeoutMs);
            PrintResultOutputs(outputs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "✗ Unexpected error in {Method}", nameof(GetLatestResult));
        }
    }

    // ── GetResultById ─────────────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>ResultManagement/GetResultById</c> (method NodeId 7002).
    /// Input: ResultId (string), Timeout (int32). Output: [ResultHandle (uint32), Result (ExtensionObject), Error (int32)].
    /// </summary>
    /// <param name="resultId">The ResultId string to look up.</param>
    /// <param name="timeoutMs">Timeout hint for the server in milliseconds (default 5000). Pass 0 for no estimate.</param>
    public void GetResultById(string resultId, int timeoutMs = 5000)
    {
        _log.LogInformation("\n── GetResultById (id={ResultId}) ──────────────────────", resultId);

        var objectId = GetResultManagementNode();
        var methodId = _js.BrowseMethod(objectId, "GetResultById",
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetResultById);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("✗ ResultManagement node or method not found.");
            return;
        }

        try
        {
            var outputs = _js.CallMethod(objectId, methodId, resultId, (int)timeoutMs);
            PrintResultOutputs(outputs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "✗ Unexpected error in {Method}", nameof(GetResultById));
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
            _log.LogWarning("⚠ Result variable subscription already active.");
            return;
        }

        _log.LogInformation("\n── Subscribing to Result variable ───────────────────");

        var rmNode = GetResultManagementNode();

        // Try to find the Results folder child, then the first variable inside
        var resultsFolder = _js.BrowseChild(rmNode, "Results");
        NodeId resultVarNode = NodeId.Null;

        if (!resultsFolder.IsNullNodeId)
        {
            // Find first variable child of Results
            _js.Session.Browse(null, null, resultsFolder, 0,
                BrowseDirection.Forward, ReferenceTypeIds.HierarchicalReferences,
                true, (uint)NodeClass.Variable, out _, out var varRefs);
            if (varRefs?.Count > 0)
                resultVarNode = (NodeId)varRefs[0].NodeId;
        }

        if (resultVarNode.IsNullNodeId)
        {
            _log.LogError("✗ Result variable node not found — skipping subscription.");
            return;
        }

        _resultVarSubscription = new Subscription(_js.Session.DefaultSubscription)
        {
            DisplayName = "IJT ResultVariable",
            PublishingInterval = _js.Config.PublishingIntervalMs,
        };

        var item = new MonitoredItem(_resultVarSubscription.DefaultItem)
        {
            DisplayName = "ResultVariable",
            StartNodeId = resultVarNode,
            AttributeId = Attributes.Value,
            SamplingInterval = 500,
        };
        item.Notification += OnResultVariableChanged;

        _resultVarSubscription.AddItem(item);
        _js.Session.AddSubscription(_resultVarSubscription);
        _resultVarSubscription.Create();

        _log.LogInformation("✓ Subscribed to Result variable ({NodeId}).", resultVarNode);
    }

    private void OnResultVariableChanged(MonitoredItem item, MonitoredItemNotificationEventArgs e)
    {
        foreach (var value in item.DequeueValues())
        {
            _log.LogInformation("[DATA] ResultVariable changed @ {Time:HH:mm:ss.fff}  Status={Status}",
                DateTime.Now, value.StatusCode);

            if (value.Value is null) continue;

            // Unwrap Variant → ExtensionObject → ResultDataType
            var raw = value.Value is Variant v ? v.Value : value.Value;
            var rd = raw is ExtensionObject eo
                ? eo.Body as UAModel.MachineryResult.ResultDataType
                : raw as UAModel.MachineryResult.ResultDataType;

            if (rd != null)
            {
                var text = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);
                IjtFileLogger.WriteResult(text);
                _log.LogInformation("  ► ResultVariable updated — full payload → {Path}",
                    IjtFileLogger.ResultLogPath);
            }
            else
            {
                _log.LogInformation("  Value: {Value}", IjtJsonSerializer.Serialize(value.Value));
            }
        }
    }

    /// <summary>Stops the result variable data-change subscription if active.</summary>
    public void StopResultVariableSubscription()
    {
        if (_resultVarSubscription == null) return;
        try
        {
            _resultVarSubscription.Delete(silent: true);
            _js.Session.RemoveSubscription(_resultVarSubscription);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "⚠ Subscription stop warning");
        }
        finally
        {
            _resultVarSubscription?.Dispose();
            _resultVarSubscription = null;
            _log.LogInformation("✓ Result variable subscription stopped.");
        }
    }

    /// <inheritdoc/>
    public void Dispose()
    {
        StopResultVariableSubscription();
        GC.SuppressFinalize(this);
    }

    // ── Output formatting ─────────────────────────────────────────────────────

    /// <summary>
    /// Writes the full result payload to file and logs a brief summary to console.
    /// Full content: logs/results/result.log.
    /// Pattern end users can copy:
    /// <code>
    ///   var rd = UnwrapResult(outputs[1]);
    ///   IjtFileLogger.WriteResult(rd != null
    ///       ? IjtResultFormatter.FormatResult(rd, DateTime.UtcNow)
    ///       : IjtJsonSerializer.FormatOutput("Result", outputs[1]));
    /// </code>
    /// </summary>
    private void PrintResultOutputs(IList<object> outputs)
    {
        if (outputs.Count == 0)
        {
            _log.LogInformation("(no output arguments)");
            return;
        }

        // Unwrap Result (outputs[1]: ExtensionObject → ResultDataType)
        var raw = outputs.Count > 1
            ? (outputs[1] is Variant vt ? vt.Value : outputs[1])
            : null;
        var rd = raw is ExtensionObject eo
            ? eo.Body as UAModel.MachineryResult.ResultDataType
            : raw as UAModel.MachineryResult.ResultDataType;

        // Write full payload to file
        var content = rd != null
            ? IjtResultFormatter.FormatResult(rd, DateTime.UtcNow)
            : IjtJsonSerializer.FormatOutput("Result", outputs.Count > 1 ? outputs[1] : null);
        IjtFileLogger.WriteResult(content);

        // Console: brief summary only
        var handle = IjtJsonSerializer.Serialize(outputs[0]);
        var error = outputs.Count > 2 ? IjtJsonSerializer.Serialize(outputs[2]) : "?";
        _log.LogInformation("✓ Result received.  ResultHandle={Handle}  Error={Error}",
            handle, error);
        _log.LogInformation("  ► Full result → {Path}", IjtFileLogger.ResultLogPath);
    }
}
