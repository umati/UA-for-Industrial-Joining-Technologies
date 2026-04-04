#nullable enable

using Opc.Ua;
using Opc.Ua.Client;
using IJT_CSharp_Client.Helpers;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// OPC UA IJT Joining Process Management operations:
/// GetJoiningProcessList, SelectJoiningProcess, and GetSelectedJoiningProgram.
/// </summary>
public sealed class JoiningProcessManagement
{
    private readonly IjtSession _s;
    private NodeId?             _jpmNodeId;

    /// <summary>Creates a JoiningProcessManagement facade backed by <paramref name="ijtSession"/>.</summary>
    public JoiningProcessManagement(IjtSession ijtSession) => _s = ijtSession;

    // ── Node lookup ───────────────────────────────────────────────────────────

    /// <summary>
    /// Finds the JoiningProcessManagement child node of the JoiningSystem instance.
    /// Falls back to the type-definition Object NodeId if browse fails.
    /// </summary>
    private NodeId GetJpmNode()
    {
        if (_jpmNodeId is not null && !_jpmNodeId.IsNullNodeId)
            return _jpmNodeId;

        var node = _s.BrowseChild(
            _s.JoiningSystemNodeId,
            UAModel.IJTBase.BrowseNames.JoiningProcessManagement);

        if (node.IsNullNodeId)
        {
            node = _s.IjtBaseObjectId(
                UAModel.IJTBase.Objects.JoiningSystemType_JoiningProcessManagement);
            Console.WriteLine("  ⚠ JoiningProcessManagement fallback to type NodeId.");
        }

        _jpmNodeId = node;
        return _jpmNodeId;
    }

    // ── GetJoiningProcessList ─────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>JoiningProcessManagement/GetJoiningProcessList</c> (NodeId 7060).
    /// No input arguments. Output: list of joining process information.
    /// </summary>
    public void GetJoiningProcessList()
    {
        Console.WriteLine("\n── GetJoiningProcessList ────────────────────────────");

        var objectId = GetJpmNode();
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            Console.WriteLine("  ✗ JoiningProcessManagement node or method not found.");
            return;
        }

        try
        {
            var outputs = _s.CallMethod(objectId, methodId);
            if (outputs.Count == 0)
            {
                Console.WriteLine("  [DATA] No output (empty list or not supported).");
                return;
            }
            Console.WriteLine($"  ✓ GetJoiningProcessList returned {outputs.Count} output(s):");
            ExtensionObjectHelper.PrintOutputArguments(outputs);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"  ✗ GetJoiningProcessList error: {ex.Message}");
        }
    }

    // ── SelectJoiningProcess ──────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>JoiningProcessManagement/SelectJoiningProcess</c> (NodeId 7065).
    /// Input: <see cref="UAModel.IJTBase.JoiningProcessIdentificationDataType"/> as ExtensionObject.
    /// </summary>
    /// <param name="joiningProcessId">Unique joining process identifier.</param>
    /// <param name="joiningProcessOriginId">Optional origin system identifier.</param>
    /// <param name="selectionName">Optional friendly selection name.</param>
    public void SelectJoiningProcess(
        string joiningProcessId,
        string joiningProcessOriginId = "",
        string selectionName = "")
    {
        Console.WriteLine($"\n── SelectJoiningProcess (id={joiningProcessId}) ──────────────");

        var objectId = GetJpmNode();
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            Console.WriteLine("  ✗ JoiningProcessManagement node or method not found.");
            return;
        }

        var jpId = new UAModel.IJTBase.JoiningProcessIdentificationDataType
        {
            JoiningProcessId       = joiningProcessId,
            JoiningProcessOriginId = joiningProcessOriginId,
            SelectionName          = selectionName,
        };
        var ext = new ExtensionObject(jpId);

        try
        {
            var outputs = _s.CallMethod(objectId, methodId, ext);
            Console.WriteLine("  ✓ SelectJoiningProcess called.");
            ExtensionObjectHelper.PrintOutputArguments(outputs);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"  ✗ SelectJoiningProcess error: {ex.Message}");
        }
    }

    // ── GetSelectedJoiningProgram ─────────────────────────────────────────────

    /// <summary>
    /// Calls <c>JoiningProcessManagement/GetSelectedJoiningProgram</c>.
    /// No input arguments. Output: JoiningProgram information.
    /// Uses <c>JoiningProcessManagementType_GetSelectedJoiningProgram</c> (NodeId 7091) as fallback.
    /// </summary>
    public void GetSelectedJoiningProgram()
    {
        Console.WriteLine("\n── GetSelectedJoiningProgram ────────────────────────");

        var jpmNode = GetJpmNode();

        // Browse for the method by name first, then fall back to type-level constant
        var methodId = _s.BrowseChild(
            jpmNode,
            UAModel.IJTBase.BrowseNames.GetSelectedJoiningProgram,
            nodeClassMask: NodeClass.Method);

        if (methodId.IsNullNodeId)
        {
            methodId = _s.IjtBaseMethodId(
                UAModel.IJTBase.Methods.JoiningProcessManagementType_GetSelectedJoiningProgram);
        }

        if (jpmNode.IsNullNodeId || methodId.IsNullNodeId)
        {
            Console.WriteLine("  ✗ JoiningProcessManagement node or method not found.");
            return;
        }

        try
        {
            var outputs = _s.CallMethod(jpmNode, methodId);
            Console.WriteLine("  ✓ GetSelectedJoiningProgram result:");
            ExtensionObjectHelper.PrintOutputArguments(outputs);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"  ✗ GetSelectedJoiningProgram error: {ex.Message}");
        }
    }
}
