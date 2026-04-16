#nullable enable

using IJT_CSharp_Client.Configuration;
using Opc.Ua;
using Opc.Ua.Client;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// Represents a connected <c>JoiningSystemType</c> instance as defined in the
/// OPC UA for Industrial Joining Technologies (IJT) companion specification.
/// </summary>
public interface IJoiningSystem
{
    // -- OPC UA session access -------------------------------------------------

    /// <summary>The underlying OPC UA SDK session.</summary>
    ISession Session { get; }

    /// <summary>Connection configuration (e.g. server URL, publishing interval).</summary>
    ClientConfig Config { get; }

    /// <summary>Returns <c>true</c> when the session is connected.</summary>
    bool IsConnected { get; }

    // -- OPC UA helpers --------------------------------------------------------

    /// <summary>
    /// Resolves a child node under <paramref name="parentId"/> by browse name.
    /// Returns <see cref="NodeId.Null"/> if not found or on any error.
    /// </summary>
    NodeId BrowseChild(
        NodeId parentId,
        string childBrowseName,
        ushort nsIndex = 0,
        NodeClass nodeClassMask = NodeClass.Unspecified);

    /// <summary>
    /// Returns all direct hierarchical children of <paramref name="parentId"/>
    /// whose <see cref="NodeClass"/> matches <paramref name="nodeClassMask"/>.
    /// Returns an empty collection on failure or when the parent is null.
    /// </summary>
    ReferenceDescriptionCollection BrowseChildren(
        NodeId parentId,
        uint nodeClassMask = (uint)NodeClass.Unspecified);

    /// <summary>
    /// Resolves a method NodeId under <paramref name="objectId"/> by browse name.
    /// Three-tier resolution: exact browse, case-insensitive enumeration, spec constant fallback.
    /// Returns <see cref="NodeId.Null"/> if all tiers fail.
    /// </summary>
    NodeId BrowseMethod(NodeId objectId, string methodBrowseName, uint fallbackConstant = 0);

    /// <summary>
    /// Browses all direct Method-class children of <paramref name="objectId"/>.
    /// Returns an empty dictionary on null input or browse failure.
    /// </summary>
    Dictionary<string, NodeId> DiscoverMethodsUnder(NodeId objectId);

    /// <summary>
    /// Calls an OPC UA method and returns output arguments.
    /// Throws <see cref="Opc.Ua.ServiceResultException"/> on Bad status codes.
    /// </summary>
    IList<object> CallMethod(NodeId objectId, NodeId methodId, params object[] inputArgs);

    // -- IJT companion spec domain ---------------------------------------------

    /// <summary>
    /// NodeId of the <c>JoiningSystem</c> instance node discovered in the server's
    /// Objects folder.
    /// </summary>
    NodeId NodeId { get; }

    /// <summary>Namespace index for <c>http://opcfoundation.org/UA/IJT/Base/</c></summary>
    ushort IjtBaseNsIdx { get; }

    /// <summary>Namespace index for <c>http://opcfoundation.org/UA/IJT/Tightening/</c></summary>
    ushort IjtTighteningNsIdx { get; }

    /// <summary>Namespace index for <c>http://opcfoundation.org/UA/Machinery/Result/</c></summary>
    ushort MachineryResultNsIdx { get; }

    /// <summary>Namespace index for <c>http://opcfoundation.org/UA/DI/</c></summary>
    ushort DiNsIdx { get; }

    /// <summary>Creates a NodeId from an IJTBase Methods constant and the runtime namespace index.</summary>
    NodeId IjtBaseMethodId(uint methodConstant);

    /// <summary>Creates a NodeId from an IJTBase Objects constant and the runtime namespace index.</summary>
    NodeId IjtBaseObjectId(uint objectConstant);

    /// <summary>Creates a NodeId from an IJTBase Variables constant and the runtime namespace index.</summary>
    NodeId IjtBaseVariableId(uint varConstant);
}
