using IJT_CSharp_Client.Domain.Events;
using IJT_CSharp_Client.Domain.Results;
using IJT_CSharp_Client.Helpers;
using IJTBase;
using MachineryResult;
using Microsoft.Extensions.Logging;
using Opc.Ua;
using Opc.Ua.Client;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// OPC UA IJT Result Management operations:
/// <list type="bullet">
///   <item>GetLatestResult  - retrieve the most recent tightening result</item>
///   <item>GetResultById    - retrieve a specific result by its ResultId</item>
///   <item>SubscribeResultVariable - monitor the live result variable via data-change subscription</item>
/// </list>
/// </summary>
public sealed class ResultManagement : IResultVariableReceiver, IResultMethodClient, IDisposable
{
    private readonly ILogger<ResultManagement> _log = IjtLog.For<ResultManagement>();
    private readonly IJoiningSystem _js;
    private Subscription? _resultVarSubscription;
    private NodeId _rmNodeId = NodeId.Null;

    /// <summary>Event raised whenever a new result is published via the live Result variable.</summary>
    public event EventHandler<DomainResultEnvelope>? OnResultVariableChanged;

    /// <summary>Creates a new ResultManagement facade backed by <paramref name="js"/>.</summary>
    public ResultManagement(IJoiningSystem js) => _js = js;

    /// <summary>True when the Result variable data-change subscription is active.</summary>
    public bool IsResultVarSubscribed => _resultVarSubscription != null;

    /// <summary>Clears the cached ResultManagement node reference so the next operation re-browses the address space.</summary>
    public void InvalidateNodeCache() => _rmNodeId = NodeId.Null;

    // -- Node lookup -----------------------------------------------------------

    /// <summary>
    /// Finds the ResultManagement object node: browses the JoiningSystem instance
    /// for a "ResultManagement" child; falls back to the type-level object NodeId.
    /// Result is cached until <see cref="InvalidateNodeCache"/> is called.
    /// </summary>
    private NodeId GetResultManagementNode()
    {
        if (!_rmNodeId.IsNullNodeId())
            return _rmNodeId;

        var child = _js.BrowseChild(_js.NodeId, UAModel.MachineryResult.BrowseNames.ResultManagement);
        if (!child.IsNullNodeId())
        {
            _rmNodeId = child;
            return _rmNodeId;
        }

        // Fallback: type-definition node (most servers honour this for method calls)
        var fallback = _js.IjtBaseObjectId(UAModel.IJTBase.Objects.JoiningSystemType_ResultManagement);
        if (!fallback.IsNullNodeId())
            _log.LogWarning("WARN ResultManagement fallback to type NodeId.");
        _rmNodeId = fallback;
        return _rmNodeId;
    }

    // -- GetLatestResult -------------------------------------------------------

    /// <summary>
    /// Calls <c>ResultManagement/GetLatestResult</c> (method NodeId 7001).
    /// Output: [ResultHandle (uint32), Result (ExtensionObject), Error (int32)].
    /// </summary>
    /// <param name="timeoutMs">Timeout hint for the server in milliseconds (default 5000). Pass 0 for no estimate.</param>
    public MethodResultResponse GetLatestResult(int timeoutMs = 5000)
    {
        _log.LogInformation("\n-- GetLatestResult ----------------------------------");

        var objectId = GetResultManagementNode();
        var methodId = _js.BrowseMethod(objectId, "GetLatestResult",
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult);

        if (objectId.IsNullNodeId() || methodId.IsNullNodeId())
        {
            var msg = "ResultManagement node or method not found.";
            _log.LogError("ERROR {Msg}", msg);
            return new MethodResultResponse(0, -1, null, false, msg);
        }

        try
        {
            var outputs = _js.CallMethod(objectId, methodId, (int)timeoutMs);
            return ParseMethodOutputs("GetLatestResult", outputs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            var msg = $"OPC UA error {IjtStatusHelper.FormatCode(srex.StatusCode)}: {srex.Message}";
            _log.LogError("ERROR {Msg}", msg);
            return new MethodResultResponse(0, unchecked((int)(uint)srex.StatusCode), null, false, msg);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(GetLatestResult));
            return new MethodResultResponse(0, -1, null, false, ex.Message);
        }
    }

    // -- GetResultById ---------------------------------------------------------

    /// <summary>
    /// Calls <c>ResultManagement/GetResultById</c> (method NodeId 7002).
    /// Input: ResultId (string), Timeout (int32). Output: [ResultHandle (uint32), Result (ExtensionObject), Error (int32)].
    /// </summary>
    /// <param name="resultId">The ResultId string to look up.</param>
    /// <param name="timeoutMs">Timeout hint for the server in milliseconds (default 5000). Pass 0 for no estimate.</param>
    public MethodResultResponse GetResultById(string resultId, int timeoutMs = 5000)
    {
        _log.LogInformation("\n-- GetResultById (id={ResultId}) ----------------------", resultId);

        var objectId = GetResultManagementNode();
        var methodId = _js.BrowseMethod(objectId, "GetResultById",
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetResultById);

        if (objectId.IsNullNodeId() || methodId.IsNullNodeId())
        {
            var msg = "ResultManagement node or method not found.";
            _log.LogError("ERROR {Msg}", msg);
            return new MethodResultResponse(0, -1, null, false, msg);
        }

        try
        {
            var outputs = _js.CallMethod(objectId, methodId, resultId, (int)timeoutMs);
            return ParseMethodOutputs("GetResultById", outputs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            var msg = $"OPC UA error {IjtStatusHelper.FormatCode(srex.StatusCode)}: {srex.Message}";
            _log.LogError("ERROR {Msg}", msg);
            return new MethodResultResponse(0, unchecked((int)(uint)srex.StatusCode), null, false, msg);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(GetResultById));
            return new MethodResultResponse(0, -1, null, false, ex.Message);
        }
    }

    // -- Subscribe to ResultVariable -------------------------------------------

    /// <summary>
    /// Creates a data-change subscription on the Result variable under
    /// <c>ResultManagement/Results</c>. Prints notifications to console.
    /// Does nothing if already subscribed.
    /// </summary>
    public void SubscribeResultVariable()
    {
        if (_resultVarSubscription != null)
        {
            _log.LogWarning("WARN Result variable subscription already active.");
            return;
        }

        _log.LogInformation("\n-- Subscribing to Result variable -------------------");

        var rmNode = GetResultManagementNode();

        // Try to find the Results folder child, then the first variable inside
        var resultsFolder = _js.BrowseChild(rmNode, "Results");
        NodeId resultVarNode = NodeId.Null;

        if (!resultsFolder.IsNullNodeId())
        {
            // Find first variable child of Results via mockable BrowseChildren
            var varRefs = _js.BrowseChildren(resultsFolder, (uint)NodeClass.Variable);
            if (varRefs?.Count > 0)
                resultVarNode = (NodeId)varRefs[0].NodeId;
        }

        if (resultVarNode.IsNullNodeId())
        {
            _log.LogError("ERROR Result variable node not found - skipping subscription.");
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
        item.Notification += OnMonitoredItemNotification;

        _resultVarSubscription.AddItem(item);
        _js.Session.AddSubscription(_resultVarSubscription);
        _resultVarSubscription.Create();

        _log.LogInformation("OK Subscribed to Result variable ({NodeId}).", resultVarNode);
    }

    private void OnMonitoredItemNotification(MonitoredItem item, MonitoredItemNotificationEventArgs e)
    {
        foreach (var value in item.DequeueValues())
        {
            ProcessResultVariableValue(value);
        }
    }

    internal bool ProcessResultVariableValue(DataValue value, Action<string>? writeResult = null)
    {
        _log.LogDebug("[DATA] ResultVariable changed @ {Time:HH:mm:ss.fff}  Status={Status}",
            DateTime.Now, value.StatusCode);

        if (value.Value is null) return false;

        // Unwrap Variant -> ExtensionObject -> ResultDataType
        var raw = value.Value is Variant v ? v.Value : value.Value;
        var rd = raw is ExtensionObject eo
            ? eo.Body as ResultDataType
            : raw as ResultDataType;

        if (rd != null)
        {
            if (!HasMeaningfulResult(rd))
            {
                _log.LogDebug("Result variable changed, but payload was empty/placeholder. Skipping file write.");
                return false;
            }

            var envelope = DomainResultMapper.MapEnvelope(rd);
            if (envelope != null)
            {
                try
                {
                    OnResultVariableChanged?.Invoke(this, envelope);
                }
                catch (Exception ex)
                {
                    _log.LogWarning(ex, "Exception in OnResultVariableChanged handler");
                }
            }

            var writer = writeResult ?? IjtFileLogger.WriteResult;
            writer(IjtJsonSerializer.FormatOutput("Result", rd));

            // Also write timestamped copy so multiple results are preserved
            var jMeta = rd.ResultMetaData as JoiningResultMetaDataType;
            var tsPath = IjtFileLogger.WriteResultTimestamped(
                IjtJsonSerializer.FormatOutput("Result", rd),
                rd.ResultMetaData?.ResultId,
                jMeta?.Name);

            _log.LogInformation("Result variable updated. Full payload logged: {Path}",
                tsPath);
            return true;
        }

        _log.LogDebug("Result variable raw value: {Value}", IjtJsonSerializer.Serialize(value.Value));
        return false;
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
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "WARN Subscription stop warning");
        }
        finally
        {
            _resultVarSubscription?.Dispose();
            _resultVarSubscription = null;
            _log.LogInformation("OK Result variable subscription stopped.");
        }
    }

    /// <inheritdoc/>
    public void Dispose()
    {
        StopResultVariableSubscription();
        GC.SuppressFinalize(this);
    }

    // -- Output formatting & Method result parsing ------------------------------

    /// <summary>
    /// Parses output arguments from GetLatestResult or GetResultById into a structured
    /// <see cref="MethodResultResponse"/>, writes the full result payload to disk, and logs summary.
    /// </summary>
    private MethodResultResponse ParseMethodOutputs(string methodName, IList<object> outputs)
    {
        if (outputs.Count == 0)
        {
            _log.LogInformation("(no output arguments)");
            return new MethodResultResponse(0, 0, null, true);
        }

        uint handle = 0;
        if (outputs.Count > 0 && outputs[0] is not null)
        {
            try { handle = Convert.ToUInt32(outputs[0]); }
            catch { handle = 0; }
        }

        // Output 1: Result (ExtensionObject -> ResultDataType)
        var raw = outputs.Count > 1
            ? (outputs[1] is Variant vt ? vt.Value : outputs[1])
            : null;
        var rd = raw is ExtensionObject eo
            ? eo.Body as ResultDataType
            : raw as ResultDataType;

        int serverError = 0;
        if (outputs.Count > 2 && outputs[2] is not null)
        {
            try { serverError = Convert.ToInt32(outputs[2]); }
            catch { serverError = 0; }
        }

        DomainResultEnvelope? domainEnvelope = null;
        if (rd is not null)
        {
            domainEnvelope = DomainResultMapper.MapEnvelope(rd);
        }

        // Write full payload to file as JSON (timestamped + latest)
        var content = IjtJsonSerializer.FormatOutput("Result", outputs.Count > 1 ? outputs[1] : null);
        var tsPath = IjtFileLogger.WriteResultTimestamped(
            content,
            domainEnvelope?.ResultId ?? rd?.ResultMetaData?.ResultId,
            domainEnvelope?.Name ?? (rd?.ResultMetaData as JoiningResultMetaDataType)?.Name);

        // Console: brief summary only
        _log.LogInformation("OK Result received.  ResultHandle={Handle}  Error={Error}",
            handle, serverError);
        _log.LogInformation("  -> Full result -> {Path}", tsPath);

        bool isSuccess = serverError == 0;
        return new MethodResultResponse(
            ResultHandle: handle,
            ServerErrorCode: serverError,
            Result: domainEnvelope,
            IsSuccess: isSuccess,
            ErrorMessage: isSuccess ? null : $"Server reported method error: {serverError}");
    }

    private void PrintResultOutputs(IList<object> outputs) => ParseMethodOutputs("", outputs);

    private static bool HasMeaningfulResult(ResultDataType rd)
    {
        if (rd.ResultMetaData is null) return false;
        if (string.IsNullOrWhiteSpace(rd.ResultMetaData.ResultId)) return false;
        // ResultContent may legitimately be empty for file-backed or reference-style results;
        // those still have valid metadata and must be written.
        return true;
    }
}
