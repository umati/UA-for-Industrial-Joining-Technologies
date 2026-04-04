#nullable enable

using IJT_CSharp_Client.Configuration;
using Opc.Ua;
using Opc.Ua.Client;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// Abstraction over <see cref="IjtSession"/> to allow unit testing of manager
/// classes without requiring a live OPC UA server connection.
/// </summary>
public interface IIjtSession
{
    /// <summary>The underlying OPC UA session.</summary>
    ISession Session { get; }

    /// <summary>Connection configuration used to create this session.</summary>
    ClientConfig Config { get; }

    /// <summary>Namespace index for <c>http://opcfoundation.org/UA/IJT/Base/</c></summary>
    ushort IjtBaseNsIdx { get; }

    /// <summary>Namespace index for <c>http://opcfoundation.org/UA/IJT/Tightening/</c></summary>
    ushort IjtTighteningNsIdx { get; }

    /// <summary>Namespace index for <c>http://opcfoundation.org/UA/Machinery/Result/</c></summary>
    ushort MachineryResultNsIdx { get; }

    /// <summary>Namespace index for <c>http://opcfoundation.org/UA/DI/</c></summary>
    ushort DiNsIdx { get; }

    /// <summary>NodeId of the JoiningSystem instance discovered in Objects folder.</summary>
    NodeId JoiningSystemNodeId { get; }

    /// <summary>Returns <c>true</c> when the underlying session is connected.</summary>
    bool IsConnected { get; }

    /// <summary>
    /// Calls an OPC UA method and returns the output arguments.
    /// </summary>
    IList<object> CallMethod(NodeId objectId, NodeId methodId, params object[] inputArgs);

    /// <summary>
    /// Resolves a child node under <paramref name="parentId"/> by browse name.
    /// Returns <see cref="NodeId.Null"/> if not found.
    /// </summary>
    NodeId BrowseChild(
        NodeId parentId,
        string childBrowseName,
        ushort nsIndex = 0,
        NodeClass nodeClassMask = NodeClass.Unspecified);

    /// <summary>Creates a NodeId from an IJTBase Methods constant and the runtime namespace index.</summary>
    NodeId IjtBaseMethodId(uint methodConstant);

    /// <summary>Creates a NodeId from an IJTBase Objects constant and the runtime namespace index.</summary>
    NodeId IjtBaseObjectId(uint objectConstant);

    /// <summary>Creates a NodeId from an IJTBase Variables constant and the runtime namespace index.</summary>
    NodeId IjtBaseVariableId(uint varConstant);
}
