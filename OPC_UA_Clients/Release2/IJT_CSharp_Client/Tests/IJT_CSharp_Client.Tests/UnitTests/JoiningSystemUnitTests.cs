#nullable enable

using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Configuration;
using Moq;
using Opc.Ua;
using Opc.Ua.Client;
using Xunit;

namespace IJT_CSharp_Client.Tests.UnitTests;

/// <summary>
/// Unit tests for <see cref="JoiningSystem"/> internal helpers — exercisable without
/// a live OPC UA server thanks to the <see cref="JoiningSystem.CreateForTesting"/> factory
/// and a mocked <see cref="ISession"/>.
/// </summary>
public sealed class JoiningSystemUnitTests
{
    // ── Helpers ───────────────────────────────────────────────────────────────

    private static Mock<ISession> CreateMockSession(bool connected = true)
    {
        var mock = new Mock<ISession>();
        mock.Setup(s => s.Connected).Returns(connected);
#pragma warning disable CS0618
        mock.Setup(s => s.DefaultSubscription).Returns(new Subscription());
#pragma warning restore CS0618
        mock.Setup(s => s.AddSubscription(It.IsAny<Subscription>())).Returns(true);
        return mock;
    }

    private static Mock<ISession> CreateMockSessionWithBrowseResult(ReferenceDescriptionCollection? refs)
    {
        var mock = CreateMockSession();
        var results = new BrowseResultCollection { new BrowseResult { References = refs } };
        var diagnostics = new DiagnosticInfoCollection();
#pragma warning disable CS0618
        mock.Setup(s => s.Browse(
                It.IsAny<RequestHeader>(),
                It.IsAny<ViewDescription>(),
                It.IsAny<uint>(),
                It.IsAny<BrowseDescriptionCollection>(),
                out results,
                out diagnostics))
            .Returns(new ResponseHeader());
#pragma warning restore CS0618
        return mock;
    }

    private static Mock<ISession> CreateMockSessionWithBrowseException(Exception exception)
    {
        var mock = CreateMockSession();
        var results = new BrowseResultCollection();
        var diagnostics = new DiagnosticInfoCollection();
#pragma warning disable CS0618
        mock.Setup(s => s.Browse(
                It.IsAny<RequestHeader>(),
                It.IsAny<ViewDescription>(),
                It.IsAny<uint>(),
                It.IsAny<BrowseDescriptionCollection>(),
                out results,
                out diagnostics))
            .Throws(exception);
#pragma warning restore CS0618
        return mock;
    }

    private static NamespaceTable CreateNamespaceTable()
    {
        var ns = new NamespaceTable();
        ns.Append(UAModel.IJTBase.Namespaces.IJTBase);
        ns.Append(UAModel.IJTTightening.Namespaces.IJTTightening);
        ns.Append(UAModel.MachineryResult.Namespaces.MachineryResult);
        ns.Append("http://opcfoundation.org/UA/DI/");
        return ns;
    }

    private static JoiningSystem CreateSession(ISession session)
        => JoiningSystem.CreateForTesting(session, new ClientConfig { ServerUrl = "opc.tcp://localhost:40451" });

    // ── CallMethod ────────────────────────────────────────────────────────────

    [Fact]
    public void CallMethod_ValidNodes_ReturnsOutputValues()
    {
        var mockSession = CreateMockSession();
        var callResults = new CallMethodResultCollection
        {
            new CallMethodResult
            {
                StatusCode = new StatusCode(StatusCodes.Good),
                OutputArguments = new VariantCollection(new[] { new Variant("output-1") }),
            }
        };
        DiagnosticInfoCollection diagInfos = [];
        mockSession
            .Setup(s => s.Call(
                It.IsAny<RequestHeader>(),
                It.IsAny<CallMethodRequestCollection>(),
                out callResults,
                out diagInfos));

        var sut = CreateSession(mockSession.Object);
        var objectId = new NodeId(1001u, 1);
        var methodId = new NodeId(1002u, 1);

        var outputs = sut.CallMethod(objectId, methodId);

        Assert.Single(outputs);
        Assert.Equal("output-1", outputs[0]);
    }

    [Fact]
    public void CallMethod_WithInputArgs_SucceedsAndReturnsOutputs()
    {
        var mockSession = CreateMockSession();
        var callResults = new CallMethodResultCollection
        {
            new CallMethodResult
            {
                StatusCode = new StatusCode(StatusCodes.Good),
                OutputArguments = new VariantCollection(),
            }
        };
        DiagnosticInfoCollection diagInfos = [];
        mockSession
            .Setup(s => s.Call(
                It.IsAny<RequestHeader>(),
                It.IsAny<CallMethodRequestCollection>(),
                out callResults,
                out diagInfos));

        var sut = CreateSession(mockSession.Object);

        var outputs = sut.CallMethod(new NodeId(100u, 1), new NodeId(200u, 1), "arg1", 42);

        Assert.Empty(outputs);
    }

    [Fact]
    public void CallMethod_NullObjectId_ThrowsInvalidOperationException()
    {
        var sut = CreateSession(CreateMockSession().Object);

        Assert.Throws<InvalidOperationException>(() =>
            sut.CallMethod(NodeId.Null, new NodeId(200u, 1)));
    }

    [Fact]
    public void CallMethod_NullMethodId_ThrowsInvalidOperationException()
    {
        var sut = CreateSession(CreateMockSession().Object);

        Assert.Throws<InvalidOperationException>(() =>
            sut.CallMethod(new NodeId(100u, 1), NodeId.Null));
    }

    [Fact]
    public void CallMethod_BadStatusCode_ThrowsServiceResultException()
    {
        var mockSession = CreateMockSession();
        var callResults = new CallMethodResultCollection
        {
            new CallMethodResult
            {
                StatusCode = new StatusCode(StatusCodes.BadNotSupported),
                OutputArguments = new VariantCollection(),
            }
        };
        DiagnosticInfoCollection diagInfos = [];
        mockSession
            .Setup(s => s.Call(
                It.IsAny<RequestHeader>(),
                It.IsAny<CallMethodRequestCollection>(),
                out callResults,
                out diagInfos));

        var sut = CreateSession(mockSession.Object);

        Assert.Throws<ServiceResultException>(() =>
            sut.CallMethod(new NodeId(100u, 1), new NodeId(200u, 1)));
    }

    [Fact]
    public void CallMethod_NoInputArgs_SucceedsWithEmptyArgList()
    {
        var mockSession = CreateMockSession();
        var callResults = new CallMethodResultCollection
        {
            new CallMethodResult
            {
                StatusCode = new StatusCode(StatusCodes.Good),
                OutputArguments = new VariantCollection(),
            }
        };
        DiagnosticInfoCollection diagInfos = [];
        mockSession
            .Setup(s => s.Call(
                It.IsAny<RequestHeader>(),
                It.IsAny<CallMethodRequestCollection>(),
                out callResults,
                out diagInfos));

        var sut = CreateSession(mockSession.Object);
        var outputs = sut.CallMethod(new NodeId(100u, 1), new NodeId(200u, 1));

        Assert.Empty(outputs);
    }

    // ── Typed NodeId factory helpers ──────────────────────────────────────────

    [Fact]
    public void IjtBaseMethodId_ReturnsNodeIdWithCorrectNsAndIdentifier()
    {
        var sut = JoiningSystem.CreateForTesting(CreateMockSession().Object, ijtBaseNsIdx: 5);

        var result = sut.IjtBaseMethodId(1234u);

        Assert.Equal(5, result.NamespaceIndex);
        Assert.Equal(1234u, (uint)result.Identifier);
    }

    [Fact]
    public void IjtBaseObjectId_ReturnsNodeIdWithCorrectNsAndIdentifier()
    {
        var sut = JoiningSystem.CreateForTesting(CreateMockSession().Object, ijtBaseNsIdx: 6);

        var result = sut.IjtBaseObjectId(5678u);

        Assert.Equal(6, result.NamespaceIndex);
        Assert.Equal(5678u, (uint)result.Identifier);
    }

    [Fact]
    public void IjtBaseVariableId_ReturnsNodeIdWithCorrectNsAndIdentifier()
    {
        var sut = JoiningSystem.CreateForTesting(CreateMockSession().Object, ijtBaseNsIdx: 8);

        var result = sut.IjtBaseVariableId(9999u);

        Assert.Equal(8, result.NamespaceIndex);
        Assert.Equal(9999u, (uint)result.Identifier);
    }

    [Fact]
    public void IjtBaseMethodId_WhenNsUnresolved_ReturnsNodeIdNull()
    {
        var sut = JoiningSystem.CreateForTesting(CreateMockSession().Object, ijtBaseNsIdx: 0);
        Assert.True(sut.IjtBaseMethodId(1234u).IsNullNodeId);
    }

    [Fact]
    public void IjtBaseObjectId_WhenNsUnresolved_ReturnsNodeIdNull()
    {
        var sut = JoiningSystem.CreateForTesting(CreateMockSession().Object, ijtBaseNsIdx: 0);
        Assert.True(sut.IjtBaseObjectId(5678u).IsNullNodeId);
    }

    [Fact]
    public void IjtBaseVariableId_WhenNsUnresolved_ReturnsNodeIdNull()
    {
        var sut = JoiningSystem.CreateForTesting(CreateMockSession().Object, ijtBaseNsIdx: 0);
        Assert.True(sut.IjtBaseVariableId(9999u).IsNullNodeId);
    }

    // ── IsConnected ───────────────────────────────────────────────────────────

    [Fact]
    public void IsConnected_WhenSessionConnected_ReturnsTrue()
    {
        var sut = CreateSession(CreateMockSession(connected: true).Object);
        Assert.True(sut.IsConnected);
    }

    [Fact]
    public void IsConnected_WhenSessionDisconnected_ReturnsFalse()
    {
        var sut = CreateSession(CreateMockSession(connected: false).Object);
        Assert.False(sut.IsConnected);
    }

    // ── OnKeepAlive ───────────────────────────────────────────────────────────

    [Fact]
    public void OnKeepAlive_GoodStatus_DoesNotThrow()
    {
        var mockSession = CreateMockSession();
        var sut = CreateSession(mockSession.Object);
        var e = new KeepAliveEventArgs(ServiceResult.Good, ServerState.Running, DateTime.UtcNow);

        var ex = Record.Exception(() => sut.OnKeepAlive(mockSession.Object, e));

        Assert.Null(ex);
    }

    [Fact]
    public void OnKeepAlive_BadStatus_DoesNotThrow()
    {
        var mockSession = CreateMockSession();
        var sut = CreateSession(mockSession.Object);
        var e = new KeepAliveEventArgs(new ServiceResult(StatusCodes.BadCommunicationError), ServerState.Unknown, DateTime.UtcNow);

        var ex = Record.Exception(() => sut.OnKeepAlive(mockSession.Object, e));

        Assert.Null(ex);
    }

    [Fact]
    public void OnKeepAlive_BadStatus_ReconnectThrowsServiceResult_DoesNotRethrow()
    {
        var mockSession = CreateMockSession();
        var sut = CreateSession(mockSession.Object);
        var e = new KeepAliveEventArgs(new ServiceResult(StatusCodes.BadCommunicationError), ServerState.Unknown, DateTime.UtcNow);

        var ex = Record.Exception(() => sut.OnKeepAlive(mockSession.Object, e));

        Assert.Null(ex);
    }

    [Fact]
    public void OnKeepAlive_BadStatus_ReconnectThrowsGenericException_DoesNotRethrow()
    {
        var mockSession = CreateMockSession();
        var sut = CreateSession(mockSession.Object);
        var e = new KeepAliveEventArgs(new ServiceResult(StatusCodes.BadCommunicationError), ServerState.Unknown, DateTime.UtcNow);

        var ex = Record.Exception(() => sut.OnKeepAlive(mockSession.Object, e));

        Assert.Null(ex);
    }

    // ── CallMethod — Uncertain status (domain-level failure, outputs still readable) ──

    [Fact]
    public void CallMethod_UncertainStatus_DoesNotThrow_AndReturnsOutputs()
    {
        var mockSession = CreateMockSession();
        var callResults = new CallMethodResultCollection
        {
            new CallMethodResult
            {
                // Uncertain = OPC UA non-Bad status; output args are valid
                StatusCode = new StatusCode(StatusCodes.UncertainInitialValue),
                OutputArguments = new VariantCollection(new[] { new Variant("domain-error-msg") }),
            }
        };
        DiagnosticInfoCollection diagInfos = [];
        mockSession
            .Setup(s => s.Call(
                It.IsAny<RequestHeader>(),
                It.IsAny<CallMethodRequestCollection>(),
                out callResults,
                out diagInfos));

        var sut = CreateSession(mockSession.Object);

        // Must NOT throw — Uncertain is not Bad
        var outputs = sut.CallMethod(new NodeId(100u, 1), new NodeId(200u, 1));

        Assert.Single(outputs);
        Assert.Equal("domain-error-msg", outputs[0]);
    }

    // ── BrowseMethod — tier ordering via null-input guards ────────────────────

    // Note: Tests that mock _session.Browse() are not possible in unit tests because
    // the synchronous Browse overload used by JoiningSystem is an extension method
    // (SessionObsolete.Browse) which Moq cannot intercept. Browse-exception and
    // tier-ordering behavior is covered by LiveIntegrationTests with a real server.
    // The tests below verify the early-return guard paths that don't require Browse.

    [Fact]
    public void BrowseMethod_AllTiersFail_NoFallbackConstant_ReturnsNodeIdNull()
    {
        // With a mock that returns null from Browse (Moq default for out params),
        // all tiers fail and fallbackConstant=0 means Tier 3 is skipped.
        var sut = JoiningSystem.CreateForTesting(CreateMockSession().Object, ijtBaseNsIdx: 7);

        var result = sut.BrowseMethod(new NodeId(5000u, 7), "NonExistentMethod");

        Assert.True(result.IsNullNodeId);
    }

    [Fact]
    public void BrowseMethod_Tier3_WhenNsUnresolved_ReturnsNodeIdNull()
    {
        // When IjtBaseNsIdx==0, IjtBaseMethodId returns NodeId.Null, so Tier 3 also
        // returns NodeId.Null regardless of the fallback constant.
        var sut = JoiningSystem.CreateForTesting(CreateMockSession().Object, ijtBaseNsIdx: 0);

        var result = sut.BrowseMethod(new NodeId(5000u, 7), "GetLatestResult", fallbackConstant: 7001u);

        Assert.True(result.IsNullNodeId);
    }

    [Fact]
    public void BrowseMethod_Tier3_WithResolvedNs_ReturnsSyntheticNodeId()
    {
        // When Tiers 1 and 2 fail (Browse returns null refs via Moq default),
        // and fallbackConstant > 0 and ns is resolved, Tier 3 returns a synthetic NodeId.
        var sut = JoiningSystem.CreateForTesting(CreateMockSession().Object, ijtBaseNsIdx: 7);

        var result = sut.BrowseMethod(new NodeId(5000u, 7), "GetLatestResult", fallbackConstant: 7001u);

        Assert.Equal((ushort)7, result.NamespaceIndex);
        Assert.Equal(7001u, (uint)result.Identifier);
    }

    // ── BrowseChild — null guard ──────────────────────────────────────────────

    [Fact]
    public void BrowseChild_NullParentId_ReturnsNodeIdNull()
    {
        var sut = CreateSession(CreateMockSession().Object);
        Assert.True(sut.BrowseChild(NodeId.Null, "AnyChild").IsNullNodeId);
    }

    [Fact]
    public void BrowseChild_MatchingBrowseNameAndNamespace_ReturnsChildNode()
    {
        var child = new NodeId(7001u, 3);
        var refs = new ReferenceDescriptionCollection
        {
            new()
            {
                BrowseName = new QualifiedName("OtherChild", 3),
                NodeId = new ExpandedNodeId(new NodeId(1u, 3)),
            },
            new()
            {
                BrowseName = new QualifiedName("TargetChild", 3),
                NodeId = new ExpandedNodeId(child),
            },
        };
        var sut = CreateSession(CreateMockSessionWithBrowseResult(refs).Object);

        var result = sut.BrowseChild(new NodeId(5000u, 3), "targetchild", nsIndex: 3);

        Assert.Equal(child, result);
    }

    [Fact]
    public void BrowseChild_WhenBrowseReturnsNullReferences_ReturnsNodeIdNull()
    {
        var sut = CreateSession(CreateMockSessionWithBrowseResult(null).Object);

        var result = sut.BrowseChild(new NodeId(5000u, 3), "MissingChild");

        Assert.True(result.IsNullNodeId);
    }

    [Fact]
    public void BrowseChild_WhenNoNamespaceMatch_ReturnsNodeIdNull()
    {
        var refs = new ReferenceDescriptionCollection
        {
            new()
            {
                BrowseName = new QualifiedName("TargetChild", 4),
                NodeId = new ExpandedNodeId(new NodeId(7001u, 4)),
            },
        };
        var sut = CreateSession(CreateMockSessionWithBrowseResult(refs).Object);

        var result = sut.BrowseChild(new NodeId(5000u, 3), "TargetChild", nsIndex: 3);

        Assert.True(result.IsNullNodeId);
    }

    [Fact]
    public void BrowseChild_WhenBrowseThrowsServiceResult_ReturnsNodeIdNull()
    {
        var sut = CreateSession(CreateMockSessionWithBrowseException(
            new ServiceResultException(StatusCodes.BadNodeIdUnknown)).Object);

        var result = sut.BrowseChild(new NodeId(5000u, 3), "TargetChild");

        Assert.True(result.IsNullNodeId);
    }

    [Fact]
    public void BrowseChild_WhenBrowseThrowsUnexpectedException_ReturnsNodeIdNull()
    {
        var sut = CreateSession(CreateMockSessionWithBrowseException(
            new InvalidOperationException("browse failed")).Object);

        var result = sut.BrowseChild(new NodeId(5000u, 3), "TargetChild");

        Assert.True(result.IsNullNodeId);
    }

    // ── BrowseChildren ───────────────────────────────────────────────────────

    [Fact]
    public void BrowseChildren_NullParentId_ReturnsEmptyCollection()
    {
        var sut = CreateSession(CreateMockSession().Object);

        var result = sut.BrowseChildren(NodeId.Null);

        Assert.Empty(result);
    }

    [Fact]
    public void BrowseChildren_WhenBrowseReturnsReferences_ReturnsReferences()
    {
        var refs = new ReferenceDescriptionCollection
        {
            new()
            {
                BrowseName = new QualifiedName("ResultManagement", 3),
                NodeId = new ExpandedNodeId(new NodeId(7002u, 3)),
            },
        };
        var sut = CreateSession(CreateMockSessionWithBrowseResult(refs).Object);

        var result = sut.BrowseChildren(new NodeId(5000u, 3), (uint)NodeClass.Object);

        Assert.Single(result);
        Assert.Equal("ResultManagement", result[0].BrowseName.Name);
    }

    [Fact]
    public void BrowseChildren_WhenBrowseReturnsNullReferences_ReturnsEmptyCollection()
    {
        var sut = CreateSession(CreateMockSessionWithBrowseResult(null).Object);

        var result = sut.BrowseChildren(new NodeId(5000u, 3));

        Assert.Empty(result);
    }

    [Fact]
    public void BrowseChildren_WhenBrowseThrowsServiceResult_ReturnsEmptyCollection()
    {
        var sut = CreateSession(CreateMockSessionWithBrowseException(
            new ServiceResultException(StatusCodes.BadSessionClosed)).Object);

        var result = sut.BrowseChildren(new NodeId(5000u, 3));

        Assert.Empty(result);
    }

    [Fact]
    public void BrowseChildren_WhenBrowseThrowsUnexpectedException_ReturnsEmptyCollection()
    {
        var sut = CreateSession(CreateMockSessionWithBrowseException(
            new InvalidOperationException("browse failed")).Object);

        var result = sut.BrowseChildren(new NodeId(5000u, 3));

        Assert.Empty(result);
    }

    // ── DiscoverMethodsUnder ─────────────────────────────────────────────────

    [Fact]
    public void DiscoverMethodsUnder_WhenBrowseReturnsMethods_ReturnsCaseInsensitiveMap()
    {
        var methodId = new NodeId(7100u, 3);
        var refs = new ReferenceDescriptionCollection
        {
            new()
            {
                BrowseName = new QualifiedName("GetLatestResult", 3),
                NodeId = new ExpandedNodeId(methodId),
            },
        };
        var sut = CreateSession(CreateMockSessionWithBrowseResult(refs).Object);

        var result = sut.DiscoverMethodsUnder(new NodeId(5000u, 3));

        Assert.True(result.ContainsKey("getlatestresult"));
        Assert.Equal(methodId, result["GETLATESTRESULT"]);
    }

    [Fact]
    public void DiscoverMethodsUnder_NullObjectId_ReturnsEmptyMap()
    {
        var sut = CreateSession(CreateMockSession().Object);

        var result = sut.DiscoverMethodsUnder(NodeId.Null);

        Assert.Empty(result);
    }

    [Fact]
    public void DiscoverMethodsUnder_WhenBrowseReturnsNullReferences_ReturnsEmptyMap()
    {
        var sut = CreateSession(CreateMockSessionWithBrowseResult(null).Object);

        var result = sut.DiscoverMethodsUnder(new NodeId(5000u, 3));

        Assert.Empty(result);
    }

    [Fact]
    public void DiscoverMethodsUnder_WhenBrowseThrows_ReturnsEmptyMap()
    {
        var sut = CreateSession(CreateMockSessionWithBrowseException(
            new InvalidOperationException("browse failed")).Object);

        var result = sut.DiscoverMethodsUnder(new NodeId(5000u, 3));

        Assert.Empty(result);
    }

    // ── ResolveNamespaceIndices via OnKeepAlive reconnect ────────────────────

    [Fact]
    public void OnKeepAlive_BadStatus_WithNamespaceUris_ResolvesIndices()
    {
        // Arrange: mock NamespaceUris so ResolveNamespaceIndices completes
        var mockSession = CreateMockSession();
        mockSession.Setup(s => s.NamespaceUris).Returns(CreateNamespaceTable());

        var sut = CreateSession(mockSession.Object);
        var e = new KeepAliveEventArgs(
            new ServiceResult(StatusCodes.BadCommunicationError),
            ServerState.Unknown,
            DateTime.UtcNow);

        // Act: OnKeepAlive triggers reconnect → ResolveNamespaceIndices → DiscoverJoiningSystem
        var ex = Record.Exception(() => sut.OnKeepAlive(mockSession.Object, e));

        // Assert: does not throw; namespace indices are resolved
        Assert.Null(ex);
        Assert.True(sut.IjtBaseNsIdx > 0);
    }

    [Fact]
    public void OnKeepAlive_BadStatus_DiscoversJoiningSystemByTypeDefinition()
    {
        var joiningSystemId = new NodeId(9100u, 4);
        var refs = new ReferenceDescriptionCollection
        {
            new()
            {
                BrowseName = new QualifiedName("JoiningSystem1", 4),
                NodeId = new ExpandedNodeId(joiningSystemId),
                TypeDefinition = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemType, 4),
            },
        };
        var mockSession = CreateMockSessionWithBrowseResult(refs);
        mockSession.Setup(s => s.NamespaceUris).Returns(CreateNamespaceTable());
        var sut = CreateSession(mockSession.Object);
        var e = new KeepAliveEventArgs(
            new ServiceResult(StatusCodes.BadCommunicationError),
            ServerState.Unknown,
            DateTime.UtcNow);

        var ex = Record.Exception(() => sut.OnKeepAlive(mockSession.Object, e));

        Assert.Null(ex);
        Assert.Equal(joiningSystemId, sut.NodeId);
    }

    [Fact]
    public void OnKeepAlive_BadStatus_DiscoveryFallsBackToFirstNonServerObject()
    {
        var fallbackId = new NodeId(9200u, 4);
        var refs = new ReferenceDescriptionCollection
        {
            new()
            {
                BrowseName = new QualifiedName("Server", 0),
                NodeId = new ExpandedNodeId(ObjectIds.Server),
                TypeDefinition = new ExpandedNodeId(ObjectTypeIds.BaseObjectType),
            },
            new()
            {
                BrowseName = new QualifiedName("ApplicationRoot", 4),
                NodeId = new ExpandedNodeId(fallbackId),
                TypeDefinition = new ExpandedNodeId(ObjectTypeIds.BaseObjectType),
            },
        };
        var mockSession = CreateMockSessionWithBrowseResult(refs);
        mockSession.Setup(s => s.NamespaceUris).Returns(CreateNamespaceTable());
        var sut = CreateSession(mockSession.Object);
        var e = new KeepAliveEventArgs(
            new ServiceResult(StatusCodes.BadCommunicationError),
            ServerState.Unknown,
            DateTime.UtcNow);

        var ex = Record.Exception(() => sut.OnKeepAlive(mockSession.Object, e));

        Assert.Null(ex);
        Assert.Equal(fallbackId, sut.NodeId);
    }

    [Fact]
    public void OnKeepAlive_BadStatus_DiscoveryWithNoObjectsLeavesNodeIdNull()
    {
        var mockSession = CreateMockSessionWithBrowseResult(new ReferenceDescriptionCollection());
        mockSession.Setup(s => s.NamespaceUris).Returns(CreateNamespaceTable());
        var sut = CreateSession(mockSession.Object);
        var e = new KeepAliveEventArgs(
            new ServiceResult(StatusCodes.BadCommunicationError),
            ServerState.Unknown,
            DateTime.UtcNow);

        var ex = Record.Exception(() => sut.OnKeepAlive(mockSession.Object, e));

        Assert.Null(ex);
        Assert.True(sut.NodeId.IsNullNodeId);
    }

    [Fact]
    public void OnKeepAlive_BadStatus_DiscoveryServiceResultExceptionDoesNotRethrow()
    {
        var mockSession = CreateMockSessionWithBrowseException(
            new ServiceResultException(StatusCodes.BadNodeIdUnknown));
        mockSession.Setup(s => s.NamespaceUris).Returns(CreateNamespaceTable());
        var sut = CreateSession(mockSession.Object);
        var e = new KeepAliveEventArgs(
            new ServiceResult(StatusCodes.BadCommunicationError),
            ServerState.Unknown,
            DateTime.UtcNow);

        var ex = Record.Exception(() => sut.OnKeepAlive(mockSession.Object, e));

        Assert.Null(ex);
        Assert.True(sut.NodeId.IsNullNodeId);
    }

    [Fact]
    public void OnKeepAlive_BadStatus_DiscoveryUnexpectedExceptionDoesNotRethrow()
    {
        var mockSession = CreateMockSessionWithBrowseException(
            new InvalidOperationException("browse failed"));
        mockSession.Setup(s => s.NamespaceUris).Returns(CreateNamespaceTable());
        var sut = CreateSession(mockSession.Object);
        var e = new KeepAliveEventArgs(
            new ServiceResult(StatusCodes.BadCommunicationError),
            ServerState.Unknown,
            DateTime.UtcNow);

        var ex = Record.Exception(() => sut.OnKeepAlive(mockSession.Object, e));

        Assert.Null(ex);
        Assert.True(sut.NodeId.IsNullNodeId);
    }

    [Fact]
    public void OnKeepAlive_BadStatus_WithEmptyNamespaceTable_SetsNsIdxToZero()
    {
        var mockSession = CreateMockSession();
        mockSession.Setup(s => s.NamespaceUris).Returns(new NamespaceTable());

        var sut = CreateSession(mockSession.Object);
        var e = new KeepAliveEventArgs(
            new ServiceResult(StatusCodes.BadCommunicationError),
            ServerState.Unknown,
            DateTime.UtcNow);

        var ex = Record.Exception(() => sut.OnKeepAlive(mockSession.Object, e));

        Assert.Null(ex);
        Assert.Equal((ushort)0, sut.IjtBaseNsIdx);
    }

    // ── BuildApplicationConfig via reflection ─────────────────────────────────

    [Fact]
    public void BuildApplicationConfig_WithDefaultConfig_ReturnsValidApplicationConfig()
    {
        var method = typeof(JoiningSystem).GetMethod(
            "BuildApplicationConfig",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
        Assert.NotNull(method);

        var config = new ClientConfig { ServerUrl = "opc.tcp://localhost:40451" };
        var appConfig = (Opc.Ua.ApplicationConfiguration)method!.Invoke(null, new object[] { config })!;

        Assert.NotNull(appConfig);
        Assert.Equal(config.ApplicationName, appConfig.ApplicationName);
        Assert.Equal(Opc.Ua.ApplicationType.Client, appConfig.ApplicationType);
        Assert.NotNull(appConfig.SecurityConfiguration);
    }

    [Fact]
    public void BuildApplicationConfig_WithCustomApplicationName_SetsNameInUri()
    {
        var method = typeof(JoiningSystem).GetMethod(
            "BuildApplicationConfig",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);

        var config = new ClientConfig
        {
            ServerUrl = "opc.tcp://localhost:40451",
            ApplicationName = "My Test Application",
        };
        var appConfig = (Opc.Ua.ApplicationConfiguration)method!.Invoke(null, new object[] { config })!;

        Assert.Contains("My-Test-Application", appConfig.ApplicationUri);
    }

    [Fact]
    public void BuildApplicationConfig_WithAutoAcceptCertificate_SetsFlag()
    {
        var method = typeof(JoiningSystem).GetMethod(
            "BuildApplicationConfig",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);

        var config = new ClientConfig
        {
            ServerUrl = "opc.tcp://localhost:40451",
            AutoAcceptServerCertificate = true,
        };
        var appConfig = (Opc.Ua.ApplicationConfiguration)method!.Invoke(null, new object[] { config })!;

        Assert.True(appConfig.SecurityConfiguration.AutoAcceptUntrustedCertificates);
    }

    [Fact]
    public void EndpointDiscoveryCacheKey_IncludesServerUrlAndSecurityMode()
    {
        var key = JoiningSystem.EndpointDiscoveryCacheKey(new ClientConfig
        {
            ServerUrl = "opc.tcp://localhost:40464",
        });

        Assert.Equal("opc.tcp://localhost:40464|security=false", key);
    }

    [Fact]
    public void EndpointDiscoveryCacheKey_DiffersByServerUrl()
    {
        var first = JoiningSystem.EndpointDiscoveryCacheKey(new ClientConfig
        {
            ServerUrl = "opc.tcp://localhost:40464",
        });
        var second = JoiningSystem.EndpointDiscoveryCacheKey(new ClientConfig
        {
            ServerUrl = "opc.tcp://localhost:40465",
        });

        Assert.NotEqual(first, second);
    }

    [Fact]
    public void ClearEndpointDiscoveryCacheForTesting_IsSafeWhenCacheIsEmpty()
    {
        var ex = Record.Exception(JoiningSystem.ClearEndpointDiscoveryCacheForTesting);

        Assert.Null(ex);
    }

    [Fact]
    public void SelectEndpointDescription_WhenCacheDisabled_CallsDiscoveryEachTime()
    {
        JoiningSystem.ClearEndpointDiscoveryCacheForTesting();
        var calls = 0;
        var config = new ClientConfig
        {
            ServerUrl = "opc.tcp://localhost:40464",
            CacheEndpointDiscovery = false,
        };

        EndpointDescription Discover() => new()
        {
            EndpointUrl = $"{config.ServerUrl}/{++calls}",
            SecurityMode = MessageSecurityMode.None,
            SecurityPolicyUri = SecurityPolicies.None,
        };

        var first = JoiningSystem.SelectEndpointDescription(config, Discover);
        var second = JoiningSystem.SelectEndpointDescription(config, Discover);

        Assert.Equal(2, calls);
        Assert.NotSame(first, second);
    }

    [Fact]
    public void SelectEndpointDescription_WhenCacheEnabled_ReusesDiscoveredEndpoint()
    {
        JoiningSystem.ClearEndpointDiscoveryCacheForTesting();
        var calls = 0;
        var config = new ClientConfig
        {
            ServerUrl = "opc.tcp://localhost:40464",
            CacheEndpointDiscovery = true,
        };

        EndpointDescription Discover() => new()
        {
            EndpointUrl = $"{config.ServerUrl}/{++calls}",
            SecurityMode = MessageSecurityMode.None,
            SecurityPolicyUri = SecurityPolicies.None,
        };

        var first = JoiningSystem.SelectEndpointDescription(config, Discover);
        var second = JoiningSystem.SelectEndpointDescription(config, Discover);

        Assert.Equal(1, calls);
        Assert.Same(first, second);
        Assert.Equal("opc.tcp://localhost:40464/1", second.EndpointUrl);
    }

    // ── DisposeAsync ──────────────────────────────────────────────────────────

    [Fact]
    public async Task DisposeAsync_WhenConnected_CloseSessionAndDispose()
    {
        var mockSession = CreateMockSession(connected: true);
        mockSession.Setup(s => s.CloseSessionAsync(
            It.IsAny<RequestHeader>(), It.IsAny<bool>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new Opc.Ua.CloseSessionResponse());

        var sut = CreateSession(mockSession.Object);

        await sut.DisposeAsync();

        mockSession.Verify(s => s.Dispose(), Times.Once);
    }

    [Fact]
    public async Task DisposeAsync_WhenNotConnected_DisposesWithoutCloseSession()
    {
        var mockSession = CreateMockSession(connected: false);
        var sut = CreateSession(mockSession.Object);

        var ex = await Record.ExceptionAsync(async () => await sut.DisposeAsync().ConfigureAwait(false));

        Assert.Null(ex);
        mockSession.Verify(s => s.Dispose(), Times.Once);
    }

    [Fact]
    public async Task DisposeAsync_WhenCloseSessionThrows_StillDisposes()
    {
        var mockSession = CreateMockSession(connected: true);
        mockSession.Setup(s => s.CloseSessionAsync(
            It.IsAny<RequestHeader>(), It.IsAny<bool>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new InvalidOperationException("close failed"));

        var sut = CreateSession(mockSession.Object);

        var ex = await Record.ExceptionAsync(async () => await sut.DisposeAsync().ConfigureAwait(false));

        Assert.Null(ex);
        mockSession.Verify(s => s.Dispose(), Times.Once);
    }
}
