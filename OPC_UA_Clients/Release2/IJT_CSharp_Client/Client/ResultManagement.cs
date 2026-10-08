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
public sealed class ResultManagement : IResultVariableReceiver, IResultMethodClient
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
    private async Task<NodeId> GetResultManagementNodeAsync()
    {
        if (!_rmNodeId.IsNull)
            return _rmNodeId;

        var child = await _js.BrowseChildAsync(_js.NodeId, MachineryResult.BrowseNames.ResultManagement);
        if (!child.IsNull)
        {
            _rmNodeId = child;
            return _rmNodeId;
        }

        // Fallback: type-definition node (most servers honour this for method calls)
        var fallback = _js.IjtBaseObjectId(IJTBase.Objects.JoiningSystemType_ResultManagement);
        if (!fallback.IsNull)
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
    public async Task<MethodResultResponse> GetLatestResultAsync(int timeoutMs = 5000)
    {
        _log.LogInformation("\n-- GetLatestResult ----------------------------------");

        var objectId = await GetResultManagementNodeAsync();
        var methodId = await _js.BrowseMethodAsync(objectId, "GetLatestResult",
            IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult);

        if (objectId.IsNull || methodId.IsNull)
        {
            var msg = "ResultManagement node or method not found.";
            _log.LogError("ERROR {Msg}", msg);
            return new MethodResultResponse(0, 0, null, MethodResultStatus.TransportError, msg);
        }

        try
        {
            var outputs = await _js.CallMethodAsync(objectId, methodId, (int)timeoutMs);
            return ParseMethodOutputs("GetLatestResult", outputs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            var msg = $"OPC UA error {IjtStatusHelper.FormatCode(srex.StatusCode)}: {srex.Message}";
            _log.LogError("ERROR {Msg}", msg);
            return new MethodResultResponse(0, 0, null, MethodResultStatus.TransportError, msg, (uint)srex.StatusCode);
        }
        catch (OperationCanceledException)
        {
            _log.LogWarning("{Method} interrupted by OperationCanceledException from the underlying operation.", nameof(GetLatestResultAsync));
            return new MethodResultResponse(0, 0, null, MethodResultStatus.Cancelled, "Operation interrupted by an OperationCanceledException (no caller cancellation token is exposed).");
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(GetLatestResultAsync));
            return new MethodResultResponse(0, 0, null, MethodResultStatus.TransportError, ex.Message);
        }
    }

    // -- GetResultById ---------------------------------------------------------

    /// <summary>
    /// Calls <c>ResultManagement/GetResultById</c> (method NodeId 7002).
    /// Input: ResultId (string), Timeout (int32). Output: [ResultHandle (uint32), Result (ExtensionObject), Error (int32)].
    /// </summary>
    /// <param name="resultId">The ResultId string to look up.</param>
    /// <param name="timeoutMs">Timeout hint for the server in milliseconds (default 5000). Pass 0 for no estimate.</param>
    public async Task<MethodResultResponse> GetResultByIdAsync(string resultId, int timeoutMs = 5000)
    {
        _log.LogInformation("\n-- GetResultById (id={ResultId}) ----------------------", resultId);

        var objectId = await GetResultManagementNodeAsync();
        var methodId = await _js.BrowseMethodAsync(objectId, "GetResultById",
            IJTBase.Methods.JoiningSystemType_ResultManagement_GetResultById);

        if (objectId.IsNull || methodId.IsNull)
        {
            var msg = "ResultManagement node or method not found.";
            _log.LogError("ERROR {Msg}", msg);
            return new MethodResultResponse(0, 0, null, MethodResultStatus.TransportError, msg);
        }

        try
        {
            var outputs = await _js.CallMethodAsync(objectId, methodId, resultId, (int)timeoutMs);
            return ParseMethodOutputs("GetResultById", outputs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            var msg = $"OPC UA error {IjtStatusHelper.FormatCode(srex.StatusCode)}: {srex.Message}";
            _log.LogError("ERROR {Msg}", msg);
            return new MethodResultResponse(0, 0, null, MethodResultStatus.TransportError, msg, (uint)srex.StatusCode);
        }
        catch (OperationCanceledException)
        {
            _log.LogWarning("{Method} interrupted by OperationCanceledException from the underlying operation.", nameof(GetResultByIdAsync));
            return new MethodResultResponse(0, 0, null, MethodResultStatus.Cancelled, "Operation interrupted by an OperationCanceledException (no caller cancellation token is exposed).");
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(GetResultByIdAsync));
            return new MethodResultResponse(0, 0, null, MethodResultStatus.TransportError, ex.Message);
        }
    }

    // -- Subscribe to ResultVariable -------------------------------------------

    /// <summary>
    /// Creates a data-change subscription on the Result variable under
    /// <c>ResultManagement/Results</c>. Prints notifications to console.
    /// Does nothing if already subscribed.
    /// </summary>
    public async Task SubscribeResultVariableAsync()
    {
        if (_resultVarSubscription != null)
        {
            _log.LogWarning("WARN Result variable subscription already active.");
            return;
        }

        _log.LogInformation("\n-- Subscribing to Result variable -------------------");

        var rmNode = await GetResultManagementNodeAsync();

        // Try to find the Results folder child, then the first variable inside
        var resultsFolder = await _js.BrowseChildAsync(rmNode, "Results");
        NodeId resultVarNode = NodeId.Null;

        if (!resultsFolder.IsNull)
        {
            // Find first variable child of Results via mockable BrowseChildren
            var varRefs = await _js.BrowseChildrenAsync(resultsFolder, (uint)NodeClass.Variable);
            if (varRefs?.Count > 0)
                resultVarNode = (NodeId)varRefs[0].NodeId;
        }

        if (resultVarNode.IsNull)
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
        await _resultVarSubscription.CreateAsync().ConfigureAwait(false);

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

        var rawValue = value.WrappedValue.AsBoxedObject(Variant.BoxingBehavior.Legacy);
        if (rawValue is null) return false;

        // Unwrap Variant -> ExtensionObject -> ResultDataType
        var raw = rawValue is Variant v
            ? v.AsBoxedObject(Variant.BoxingBehavior.Legacy)
            : rawValue;
        var rd = raw is ExtensionObject eo
            ? ExtensionObjectHelper.TryDecode<ResultDataType>(eo)
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

        _log.LogDebug("Result variable raw value: {Value}", IjtJsonSerializer.Serialize(rawValue));
        return false;
    }

    /// <summary>Stops the result variable data-change subscription if active.</summary>
    public async Task StopResultVariableSubscriptionAsync()
    {
        var subscription = _resultVarSubscription;
        if (subscription == null) return;
        _resultVarSubscription = null;
        try
        {
            await subscription.DeleteAsync(silent: true).ConfigureAwait(false);
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
        try
        {
            await _js.Session.RemoveSubscriptionAsync(subscription).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "WARN Removing the result-variable subscription from the session failed");
        }
        finally
        {
            subscription.Dispose();
            _log.LogInformation("OK Result variable subscription stopped.");
        }
    }

    /// <inheritdoc/>
    public async ValueTask DisposeAsync()
    {
        await StopResultVariableSubscriptionAsync().ConfigureAwait(false);
        GC.SuppressFinalize(this);
    }

    // -- Output formatting & Method result parsing ------------------------------

    /// <summary>
    /// Parses output arguments from GetLatestResult or GetResultById into a structured
    /// <see cref="MethodResultResponse"/>, writes the full result payload to disk, and logs summary.
    /// </summary>
    private MethodResultResponse ParseMethodOutputs(string methodName, IList<object> outputs)
    {
        // Output contract: [ResultHandle (uint32), Result (ExtensionObject), Error (int32)].
        // The NodeSet declares exactly three outputs; any other count is malformed.
        if (outputs.Count != 3)
        {
            var msg = $"{methodName}: malformed response - expected exactly 3 output arguments, received {outputs.Count}.";
            _log.LogError("ERROR {Msg}", msg);
            return new MethodResultResponse(0, 0, null, MethodResultStatus.MalformedResponse, msg);
        }

        if (!TryGetOutput(outputs[0], out uint handle))
        {
            var msg = $"{methodName}: malformed response - ResultHandle output is missing or not a uint32.";
            _log.LogError("ERROR {Msg}", msg);
            return new MethodResultResponse(0, 0, null, MethodResultStatus.MalformedResponse, msg);
        }

        if (!TryGetOutput(outputs[2], out int serverError))
        {
            var msg = $"{methodName}: malformed response - Error output is missing or not an int32.";
            _log.LogError("ERROR {Msg}", msg);
            return new MethodResultResponse(handle, 0, null, MethodResultStatus.MalformedResponse, msg);
        }

        // Output 1: Result (ExtensionObject -> ResultDataType)
        var raw = outputs[1] is Variant vt
            ? vt.AsBoxedObject(Variant.BoxingBehavior.Legacy)
            : outputs[1];
        var rd = raw is ExtensionObject eo
            ? ExtensionObjectHelper.TryDecode<ResultDataType>(eo)
            : raw as ResultDataType;

        if (serverError == 0 && rd is null)
        {
            var msg = $"{methodName}: malformed response - server reported success but Result is absent or not a ResultDataType.";
            _log.LogError("ERROR {Msg}", msg);
            return new MethodResultResponse(handle, 0, null, MethodResultStatus.MalformedResponse, msg);
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

        // Console: brief summary only; success and server-reported errors are logged distinctly.
        if (serverError == 0)
        {
            _log.LogInformation("OK Result received.  ResultHandle={Handle}  Error={Error}",
                handle, serverError);
        }
        else
        {
            _log.LogWarning("WARN {Method}: server reported method error.  ResultHandle={Handle}  Error={Error}",
                methodName, handle, serverError);
        }
        _log.LogInformation("  -> Full result -> {Path}", tsPath);

        var isSuccess = serverError == 0;
        return new MethodResultResponse(
            ResultHandle: handle,
            ServerErrorCode: serverError,
            Result: domainEnvelope,
            Status: isSuccess ? MethodResultStatus.Success : MethodResultStatus.ServerError,
            ErrorMessage: isSuccess ? null : $"Server reported method error: {serverError}");
    }

    /// <summary>
    /// Strict runtime type check of one OPC UA output argument (after unwrapping a <see cref="Variant"/>).
    /// No coercion: numeric strings, floating-point values and other numeric widths are rejected.
    /// </summary>
    private static bool TryGetOutput(object? value, out uint result)
    {
        if (value is Variant variant)
            return variant.TryGetValue(out result);
        if (value is uint typed)
        {
            result = typed;
            return true;
        }
        result = default;
        return false;
    }

    private static bool TryGetOutput(object? value, out int result)
    {
        if (value is Variant variant)
            return variant.TryGetValue(out result);
        var unwrapped = value is Variant v
            ? v.AsBoxedObject(Variant.BoxingBehavior.Legacy)
            : value;
        if (unwrapped is int typed)
        {
            result = typed;
            return true;
        }

        result = default!;
        return false;
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
