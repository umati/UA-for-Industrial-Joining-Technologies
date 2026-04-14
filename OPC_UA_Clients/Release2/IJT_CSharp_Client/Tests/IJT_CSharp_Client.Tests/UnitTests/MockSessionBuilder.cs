#nullable enable

using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Configuration;
using Moq;
using Opc.Ua;
using Opc.Ua.Client;

namespace IJT_CSharp_Client.Tests.UnitTests;

/// <summary>
/// Shared Moq-based factory for building a mock <see cref="IJoiningSystem"/> in unit tests.
/// </summary>
internal static class MockSessionBuilder
{
    /// <summary>A NodeId that is "valid" (not Null) — used as the default return for node lookups.</summary>
    public static readonly NodeId ValidNodeId = new NodeId(9999u, 1);

    /// <summary>A second valid NodeId — used for method IDs to avoid collisions with object IDs.</summary>
    public static readonly NodeId ValidMethodId = new NodeId(8888u, 1);

    /// <summary>
    /// Creates a fully configured mock <see cref="IJoiningSystem"/>.
    /// </summary>
    public static Mock<IJoiningSystem> Create(
        NodeId? browseChildResult = null,
        NodeId? methodResult = null,
        IList<object>? callMethodResult = null)
    {
        var session = new Mock<IJoiningSystem>();

        session.Setup(s => s.Config).Returns(new ClientConfig
        {
            ServerUrl = "opc.tcp://localhost:40451",
            PublishingIntervalMs = 500,
        });

        session.Setup(s => s.NodeId).Returns(ValidNodeId);
        session.Setup(s => s.IjtBaseNsIdx).Returns(7);
        session.Setup(s => s.IjtTighteningNsIdx).Returns(8);
        session.Setup(s => s.MachineryResultNsIdx).Returns(6);

        session.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(browseChildResult ?? ValidNodeId);

        session.Setup(s => s.DiscoverMethodsUnder(It.IsAny<NodeId>()))
            .Returns(new Dictionary<string, NodeId>(StringComparer.OrdinalIgnoreCase));

        session.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>()))
            .Returns(methodResult ?? ValidMethodId);

        session.Setup(s => s.BrowseMethod(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .Returns(methodResult ?? ValidMethodId);

        session.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>()))
            .Returns(browseChildResult ?? ValidNodeId);

        session.Setup(s => s.IjtBaseVariableId(It.IsAny<uint>()))
            .Returns(browseChildResult ?? ValidNodeId);

        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(callMethodResult ?? new List<object>());

        // Mock ISession with enough surface for subscription-heavy code paths
        var mockSession = new Mock<ISession>();
#pragma warning disable CS0618
        mockSession.Setup(s => s.DefaultSubscription).Returns(new Subscription());
        mockSession.Setup(s => s.AddSubscription(It.IsAny<Subscription>())).Returns(true);
#pragma warning restore CS0618
        session.Setup(s => s.Session).Returns(mockSession.Object);

        return session;
    }

    /// <summary>
    /// Creates a session mock where ALL node lookups return <see cref="NodeId.Null"/> (not found).
    /// </summary>
    public static Mock<IJoiningSystem> CreateWithNullNodes()
        => Create(browseChildResult: NodeId.Null, methodResult: NodeId.Null);
}
