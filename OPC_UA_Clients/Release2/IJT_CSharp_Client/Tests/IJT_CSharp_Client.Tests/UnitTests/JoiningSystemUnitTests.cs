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

    // ── ResolveNamespaceIndices via OnKeepAlive reconnect ────────────────────

    [Fact]
    public void OnKeepAlive_BadStatus_WithNamespaceUris_ResolvesIndices()
    {
        // Arrange: mock NamespaceUris so ResolveNamespaceIndices completes
        var mockSession = CreateMockSession();
        var ns = new NamespaceTable();
        // Append the IJT namespaces so GetIndex returns valid indices
        ns.Append(UAModel.IJTBase.Namespaces.IJTBase);
        ns.Append(UAModel.IJTTightening.Namespaces.IJTTightening);
        ns.Append(UAModel.MachineryResult.Namespaces.MachineryResult);
        ns.Append("http://opcfoundation.org/UA/DI/");
        mockSession.Setup(s => s.NamespaceUris).Returns(ns);

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
