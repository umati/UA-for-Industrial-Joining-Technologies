#nullable enable

using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;
using Opc.Ua;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// OPC UA IJT Simulation methods — fire synthetic results and events directly from the simulator.
/// Node path: JoiningSystem / Simulations / SimulateResults  (result simulation methods)
///            JoiningSystem / Simulations / SimulateEventsAndConditions  (event simulation methods)
/// All nodes are in the Application namespace (NS_APP, ns=1 at runtime).
/// </summary>
public sealed class SimulationManagement : IDisposable
{
    private readonly ILogger<SimulationManagement> _log = IjtLog.For<SimulationManagement>();
    private readonly IJoiningSystem _js;

    // Cached node references — cleared on InvalidateNodeCache()
    private NodeId? _simulationsNodeId;
    private NodeId? _simulateResultsNodeId;
    private NodeId? _simulateEventsNodeId;

    /// <summary>Creates a SimulationManagement facade backed by <paramref name="js"/>.</summary>
    public SimulationManagement(IJoiningSystem js) => _js = js;

    /// <summary>Clears cached node references so the next operation re-browses the address space.</summary>
    public void InvalidateNodeCache()
    {
        _simulationsNodeId = null;
        _simulateResultsNodeId = null;
        _simulateEventsNodeId = null;
    }

    // -- Node lookup -----------------------------------------------------------

    private NodeId GetSimulationsNode()
    {
        if (_simulationsNodeId is not null && !_simulationsNodeId.IsNullNodeId)
            return _simulationsNodeId;

        var node = _js.BrowseChild(_js.NodeId, "Simulations");
        if (node.IsNullNodeId)
            _log.LogWarning("WARN Simulations node not found under JoiningSystem.");
        _simulationsNodeId = node;
        return _simulationsNodeId;
    }

    private NodeId GetSimulateResultsNode()
    {
        if (_simulateResultsNodeId is not null && !_simulateResultsNodeId.IsNullNodeId)
            return _simulateResultsNodeId;

        var simsNode = GetSimulationsNode();
        if (simsNode.IsNullNodeId) return (_simulateResultsNodeId = NodeId.Null);

        var node = _js.BrowseChild(simsNode, "SimulateResults");
        if (node.IsNullNodeId)
            _log.LogWarning("WARN SimulateResults node not found under Simulations.");
        _simulateResultsNodeId = node;
        return _simulateResultsNodeId;
    }

    private NodeId GetSimulateEventsNode()
    {
        if (_simulateEventsNodeId is not null && !_simulateEventsNodeId.IsNullNodeId)
            return _simulateEventsNodeId;

        var simsNode = GetSimulationsNode();
        if (simsNode.IsNullNodeId) return (_simulateEventsNodeId = NodeId.Null);

        // Try both possible browse names the server may use
        var node = _js.BrowseChild(simsNode, "SimulateEventsAndConditions");
        if (node.IsNullNodeId)
            node = _js.BrowseChild(simsNode, "SimulateEvents");
        if (node.IsNullNodeId)
            _log.LogWarning("WARN SimulateEventsAndConditions node not found under Simulations.");
        _simulateEventsNodeId = node;
        return _simulateEventsNodeId;
    }

    // -- SimulateSingleResult --------------------------------------------------

    /// <summary>
    /// Calls Simulations/SimulateResults/SimulateSingleResult.
    /// REAL implementation: fires a result + ResultReady event immediately.
    /// </summary>
    /// <param name="resultType">
    /// 0=SIMPLE_OK, 1=ONE_STEP_OK, 2=MULTI_STEP_OK (4-step program),
    /// 3=MULTI_STEP_NOK_FAILING, 4=MULTI_STEP_NOK_TRIGGER_LOST.
    /// Values out of range default to type 0.
    /// </param>
    /// <param name="includeTraces">When true, trace data is included in the result payload.</param>
    public void SimulateSingleResult(uint resultType = 0, bool includeTraces = false)
    {
        _log.LogInformation("\n-- SimulateSingleResult (type={Type}, traces={Traces}) --",
            resultType, includeTraces);

        var objectId = GetSimulateResultsNode();
        var methodId = _js.BrowseMethod(objectId, "SimulateSingleResult");

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("ERROR Simulations/SimulateResults node or SimulateSingleResult method not found.");
            return;
        }

        try
        {
            _js.CallMethod(objectId, methodId, resultType, includeTraces);
            _log.LogInformation("OK SimulateSingleResult fired (type={Type}, includeTraces={Traces}). " +
                "Result will arrive via ResultReady event subscription.", resultType, includeTraces);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SimulateSingleResult));
        }
    }

    // -- SimulateBatchOrSyncResult ---------------------------------------------

    /// <summary>
    /// Calls Simulations/SimulateResults/SimulateBatch_Or_Sync_Result.
    /// REAL implementation: fires a batch (3) or sync (2) result.
    /// </summary>
    /// <param name="classification">2=SYNC, 3=BATCH (default). Invalid values default to BATCH.</param>
    /// <param name="numChildren">Number of child results (default 3).</param>
    /// <param name="includeTraces">When true, traces included in child results.</param>
    /// <param name="sendAsReferences">When true, child results sent as references instead of inline.</param>
    public void SimulateBatchOrSyncResult(byte classification = 3, uint numChildren = 3,
        bool includeTraces = false, bool sendAsReferences = false)
    {
        _log.LogInformation(
            "\n-- SimulateBatchOrSyncResult (class={Class}, children={N}, traces={T}, refs={R}) --",
            classification, numChildren, includeTraces, sendAsReferences);

        var objectId = GetSimulateResultsNode();
        var methodId = _js.BrowseMethod(objectId, "SimulateBatch_Or_Sync_Result");

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("ERROR Simulations/SimulateResults node or SimulateBatch_Or_Sync_Result method not found.");
            return;
        }

        try
        {
            _js.CallMethod(objectId, methodId, classification, numChildren, includeTraces, sendAsReferences);
            _log.LogInformation("OK SimulateBatch_Or_Sync_Result fired (classification={Class}).",
                classification == 2 ? "SYNC" : "BATCH");
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SimulateBatchOrSyncResult));
        }
    }

    // -- SimulateJobResult -----------------------------------------------------

    /// <summary>
    /// Calls Simulations/SimulateResults/SimulateJobResult.
    /// REAL implementation: fires a job result.
    /// </summary>
    /// <param name="sendAsReferences">When true, child results sent as references.</param>
    public void SimulateJobResult(bool sendAsReferences = false)
    {
        _log.LogInformation("\n-- SimulateJobResult (sendAsRefs={Refs}) --", sendAsReferences);

        var objectId = GetSimulateResultsNode();
        var methodId = _js.BrowseMethod(objectId, "SimulateJobResult");

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("ERROR Simulations/SimulateResults node or SimulateJobResult method not found.");
            return;
        }

        try
        {
            _js.CallMethod(objectId, methodId, sendAsReferences);
            _log.LogInformation("OK SimulateJobResult fired (sendAsReferences={Refs}).", sendAsReferences);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SimulateJobResult));
        }
    }

    // -- SimulateBulkResults ---------------------------------------------------

    /// <summary>
    /// Calls Simulations/SimulateResults/SimulateBulkResults.
    /// REAL implementation: fires many results in a background thread on the server.
    /// Constraint: toSeq must be >= fromSeq+5; minDurationMs >= 100.
    /// </summary>
    /// <param name="resultType">Type code (0–4). See SimulateSingleResult for codes.</param>
    /// <param name="includeTraces">Include trace data in each result.</param>
    /// <param name="fromSeq">Starting sequence number.</param>
    /// <param name="toSeq">Ending sequence number (must be &gt;= fromSeq+5).</param>
    /// <param name="minDurationMs">Minimum delay between results in ms (must be &gt;= 100).</param>
    /// <param name="updateResultVariables">When true, updates ResultManagement result variables.</param>
    public void SimulateBulkResults(uint resultType = 0, bool includeTraces = false,
        ulong fromSeq = 1, ulong toSeq = 10, long minDurationMs = 500, bool updateResultVariables = true)
    {
        _log.LogInformation(
            "\n-- SimulateBulkResults (type={T}, from={F}, to={To}, interval={I}ms) --",
            resultType, fromSeq, toSeq, minDurationMs);

        if (toSeq < fromSeq + 5)
        {
            _log.LogError("ERROR toSeq must be >= fromSeq+5 (fromSeq={F}, toSeq={To}).", fromSeq, toSeq);
            return;
        }
        if (minDurationMs < 100)
        {
            _log.LogError("ERROR minDurationMs must be >= 100 (got {Ms}).", minDurationMs);
            return;
        }

        var objectId = GetSimulateResultsNode();
        var methodId = _js.BrowseMethod(objectId, "SimulateBulkResults");

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("ERROR Simulations/SimulateResults node or SimulateBulkResults method not found.");
            return;
        }

        try
        {
            _js.CallMethod(objectId, methodId,
                resultType, includeTraces, fromSeq, toSeq, minDurationMs, updateResultVariables);
            _log.LogInformation("OK SimulateBulkResults started on server: {Count} results, ~{Delay}ms each.",
                toSeq - fromSeq + 1, minDurationMs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SimulateBulkResults));
        }
    }

    // -- SimulateEvents --------------------------------------------------------

    /// <summary>
    /// Calls Simulations/SimulateEventsAndConditions/SimulateEvents.
    /// REAL implementation: fires exactly 1 event of the given type.
    /// </summary>
    /// <param name="eventType">
    /// Event type code (1–60). Representative values:
    /// 1=TOOL_CONNECTED, 6=TOOL_STARTED, 13=TOOL_NOT_AVAILABLE_ERROR,
    /// 29=PROGRAM_SELECTED, 31=EXECUTION_STARTED, 38=RECEIVED_IDENTIFIER.
    /// </param>
    public void SimulateEvent(uint eventType = 1)
    {
        _log.LogInformation("\n-- SimulateEvents (eventType={Type}) --", eventType);

        var objectId = GetSimulateEventsNode();
        var methodId = _js.BrowseMethod(objectId, "SimulateEvents");

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("ERROR SimulateEventsAndConditions node or SimulateEvents method not found.");
            return;
        }

        try
        {
            _js.CallMethod(objectId, methodId, eventType);
            _log.LogInformation("OK SimulateEvents fired (eventType={Type}).", eventType);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SimulateEvent));
        }
    }

    // -- SimulateBulkEvents ----------------------------------------------------

    /// <summary>
    /// Calls Simulations/SimulateEventsAndConditions/SimulateBulkEvents.
    /// REAL implementation: fires <paramref name="count"/> events of the given type.
    /// Maximum count is 1000.
    /// </summary>
    /// <param name="eventType">Event type code (1–60). See <see cref="SimulateEvent"/> for codes.</param>
    /// <param name="count">Number of events to fire (1–1000).</param>
    public void SimulateBulkEvents(uint eventType = 1, uint count = 10)
    {
        _log.LogInformation("\n-- SimulateBulkEvents (eventType={Type}, count={Count}) --", eventType, count);

        if (count == 0 || count > 1000)
        {
            _log.LogError("ERROR count must be between 1 and 1000 (got {Count}).", count);
            return;
        }

        var objectId = GetSimulateEventsNode();
        var methodId = _js.BrowseMethod(objectId, "SimulateBulkEvents");

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("ERROR SimulateEventsAndConditions node or SimulateBulkEvents method not found.");
            return;
        }

        try
        {
            _js.CallMethod(objectId, methodId, eventType, count);
            _log.LogInformation("OK SimulateBulkEvents fired ({Count} events of type {Type}).", count, eventType);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SimulateBulkEvents));
        }
    }

    /// <inheritdoc/>
    public void Dispose()
    {
        GC.SuppressFinalize(this);
    }
}
