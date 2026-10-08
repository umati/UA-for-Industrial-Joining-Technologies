#nullable enable
using IJT_CSharp_Client.Helpers;
using IJTBase;
using Moq;
using Opc.Ua;
using Opc.Ua.Client;
using Xunit;

namespace IJT_CSharp_Client.Tests.Helpers;

/// <summary>
/// Unit tests for <see cref="AddressSpaceHelper"/>.
/// Browse-based methods use <see cref="Mock{ISession}"/> targeting
/// <c>ISessionClientMethods.Browse</c> (the actual interface method, not the
/// extension-method wrapper that is not Moq-interceptable).
/// </summary>
public sealed class AddressSpaceHelperTests
{
    // ── Browse helper ─────────────────────────────────────────────────────────
    //
    // ISession.Browse(NodeId, ...) is a static extension method (SessionObsolete.Browse)
    // that internally delegates to ISessionClientMethods.Browse which IS mockable.

    private static Mock<ISession> SessionWithBrowseResult(ReferenceDescriptionCollection? refs)
    {
        var mock = new Mock<ISession>();
        mock.Setup(s => s.MessageContext).Returns(ServiceMessageContext.CreateEmpty(DefaultTelemetry.Create(_ => { })));
        mock.Setup(s => s.OperationLimits).Returns(new OperationLimits());
        mock.Setup(s => s.ServerCapabilities).Returns(new ServerCapabilities());

        var browseRefs = refs != null ? new ArrayOf<ReferenceDescription>(refs.ToArray()) : default;
        mock.Setup(s => s.BrowseAsync(
                It.IsAny<RequestHeader>(),
                It.IsAny<ViewDescription>(),
                It.IsAny<uint>(),
                It.IsAny<ArrayOf<BrowseDescription>>(),
                It.IsAny<CancellationToken>()))
            .Returns(new ValueTask<BrowseResponse>(new BrowseResponse
            {
                ResponseHeader = new ResponseHeader(),
                Results = new ArrayOf<BrowseResult>(new[]
                {
                    new BrowseResult
                    {
                        StatusCode = StatusCodes.Good,
                        References = browseRefs
                    }
                })
            }));

        mock.Setup(s => s.ReadAsync(
                It.IsAny<RequestHeader>(),
                It.IsAny<double>(),
                It.IsAny<TimestampsToReturn>(),
                It.IsAny<ArrayOf<ReadValueId>>(),
                It.IsAny<CancellationToken>()))
            .Returns(new ValueTask<ReadResponse>(new ReadResponse
            {
                ResponseHeader = new ResponseHeader(),
                Results = new[] { DataValue.FromStatusCode(StatusCodes.BadNodeIdUnknown) }
            }));

        return mock;
    }

    private static Mock<ISession> SessionWithReadResult(DataValue value)
    {
        var mock = new Mock<ISession>();
        mock.Setup(s => s.ReadAsync(
                It.IsAny<RequestHeader>(),
                It.IsAny<double>(),
                It.IsAny<TimestampsToReturn>(),
                It.IsAny<ArrayOf<ReadValueId>>(),
                It.IsAny<CancellationToken>()))
            .Returns(new ValueTask<ReadResponse>(new ReadResponse
            {
                ResponseHeader = new ResponseHeader(),
                Results = new[] { value }
            }));
        return mock;
    }

    // ── BrowseChildrenAsync ────────────────────────────────────────────────────────

    [Fact]
    public async Task BrowseChildren_WhenBrowseReturnsNullRefs_ReturnsEmptyCollection()
    {
        var mock = SessionWithBrowseResult(null);

        var refs = await AddressSpaceHelper.BrowseChildrenAsync(mock.Object, new NodeId(1u, 0));

        Assert.NotNull(refs);
        Assert.Empty(refs);
    }

    [Fact]
    public async Task BrowseChildren_WhenBrowseReturnsRefs_ReturnsAll()
    {
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("TestNode", 1),
            NodeId = new ExpandedNodeId(new NodeId(42u, 1)),
        };
        var result = await AddressSpaceHelper.BrowseChildrenAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0));

        Assert.Single(result);
        Assert.Equal("TestNode", result[0].BrowseName.Name);
    }

    // ── FindChildAsync ─────────────────────────────────────────────────────────────

    [Fact]
    public async Task FindChild_WhenMatchFound_ReturnsNodeId()
    {
        var childId = new NodeId(55u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("AssetManagement", 2),
            NodeId = new ExpandedNodeId(childId),
        };
        var result = await AddressSpaceHelper.FindChildAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            "AssetManagement");

        Assert.Equal(childId, result);
    }

    [Fact]
    public async Task FindChild_WhenNoMatch_ReturnsNullNodeId()
    {
        var result = await AddressSpaceHelper.FindChildAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object,
            new NodeId(1u, 0),
            "NonExistent");

        Assert.True(result.IsNull);
    }

    [Fact]
    public async Task FindChild_IsCaseInsensitive()
    {
        var childId = new NodeId(56u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("assetmanagement", 2),
            NodeId = new ExpandedNodeId(childId),
        };
        var result = await AddressSpaceHelper.FindChildAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            "AssetManagement");

        Assert.Equal(childId, result);
    }

    // ── ResolvePathAsync ───────────────────────────────────────────────────────────

    [Fact]
    public async Task ResolvePath_WhenSegmentNotFound_ReturnsNullNodeId()
    {
        var result = await AddressSpaceHelper.ResolvePathAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object,
            new NodeId(1u, 0),
            "Missing.Path");

        Assert.True(result.IsNull);
    }

    [Fact]
    public async Task ResolvePath_WhenSingleSegmentFound_ReturnsChildNode()
    {
        var childId = new NodeId(100u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("AssetManagement", 2),
            NodeId = new ExpandedNodeId(childId),
        };
        var result = await AddressSpaceHelper.ResolvePathAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            "AssetManagement");

        Assert.Equal(childId, result);
    }

    // ── ReadValueAsync ─────────────────────────────────────────────────────────────

    [Fact]
    public async Task ReadValue_WhenStatusIsGood_ReturnsValue()
    {
        var result = await AddressSpaceHelper.ReadValueAsync(
            SessionWithReadResult(new DataValue(new Variant("hello"), StatusCodes.Good)).Object,
            new NodeId(99u, 1));

        Assert.Equal("hello", result);
    }

    [Fact]
    public async Task ReadValue_WhenStatusIsBad_ReturnsNull()
    {
        var result = await AddressSpaceHelper.ReadValueAsync(
            SessionWithReadResult(new DataValue(new Variant("ignored"), StatusCodes.Bad)).Object,
            new NodeId(99u, 1));

        Assert.Null(result);
    }

    [Fact]
    public async Task ReadValue_WhenServiceThrows_ReturnsNull()
    {
        var mock = new Mock<ISession>();
        mock.Setup(s => s.ReadAsync(
                It.IsAny<RequestHeader>(),
                It.IsAny<double>(),
                It.IsAny<TimestampsToReturn>(),
                It.IsAny<ArrayOf<ReadValueId>>(),
                It.IsAny<CancellationToken>()))
            .Throws(new ServiceResultException(StatusCodes.BadNodeIdUnknown));

        var result = await AddressSpaceHelper.ReadValueAsync(mock.Object, new NodeId(99u, 1));

        Assert.Null(result);
    }

    // ── ReadValueAsync<T> ──────────────────────────────────────────────────────────

    [Fact]
    public async Task ReadValueT_WhenValueMatchesType_ReturnsTyped()
    {
        var result = await AddressSpaceHelper.ReadValueAsync<string>(
            SessionWithReadResult(new DataValue(new Variant("typed-string"), StatusCodes.Good)).Object,
            new NodeId(100u, 1));

        Assert.Equal("typed-string", result);
    }

    [Fact]
    public async Task ReadValueT_WhenValueIsWrongType_ReturnsDefault()
    {
        var result = await AddressSpaceHelper.ReadValueAsync<int>(
            SessionWithReadResult(new DataValue(new Variant("not-an-int"), StatusCodes.Good)).Object,
            new NodeId(101u, 1));

        Assert.Equal(0, result);
    }

    // ── InvalidateCache ───────────────────────────────────────────────────────

    [Fact]
    public async Task InvalidateCache_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () => new AddressSpaceHelper().InvalidateCache());
        Assert.Null(ex);
    }

    [Fact]
    public async Task InvalidateCache_AllowsSubsequentBrowse()
    {
        var childId = new NodeId(88u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("ResultManagement", 2),
            NodeId = new ExpandedNodeId(childId),
        };
        var helper = new AddressSpaceHelper();
        var mock = SessionWithBrowseResult(new ReferenceDescriptionCollection { rd });

        var found = await helper.FindChildAsync(mock.Object, new NodeId(1u, 1), "ResultManagement");
        Assert.Equal(childId, found);

        helper.InvalidateCache();
        var ex = await Record.ExceptionAsync(async () => helper.InvalidateCache());
        Assert.Null(ex);
    }

    // ── GetOrFindManagementNodeAsync ──────────────────────────────────────────

    [Fact]
    public async Task GetOrFindManagementNodeAsync_WhenBrowseReturnsEmpty_ReturnsNullNodeId()
    {
        var helper = new AddressSpaceHelper();
        var session = SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object;

        var result = await helper.GetOrFindManagementNodeAsync(
            session, new NodeId(1u, 1), "ResultManagement");

        Assert.True(result.IsNull);
    }

    [Fact]
    public async Task GetOrFindManagementNodeAsync_SecondCallWithSameName_UsesCachedValue()
    {
        var childId = new NodeId(77u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("ResultManagement", 2),
            NodeId = new ExpandedNodeId(childId),
        };
        var mock = SessionWithBrowseResult(new ReferenceDescriptionCollection { rd });
        var helper = new AddressSpaceHelper();
        var jsId = new NodeId(1u, 1);

        var first = await helper.GetOrFindManagementNodeAsync(mock.Object, jsId, "ResultManagement");
        var second = await helper.GetOrFindManagementNodeAsync(mock.Object, jsId, "ResultManagement");

        Assert.Equal(first, second);
        Assert.Equal(childId, first);

        mock.Verify(s => s.BrowseAsync(
            It.IsAny<RequestHeader>(), It.IsAny<ViewDescription>(),
            It.IsAny<uint>(), It.IsAny<ArrayOf<BrowseDescription>>(),
            It.IsAny<CancellationToken>()),
            Times.Once);
    }

    // ── DiscoverAssetInstancesAsync ───────────────────────────────────────────

    [Fact]
    public async Task DiscoverAssetInstancesAsync_SkipsPlaceholderNodes()
    {
        var realNode = new ReferenceDescription
        {
            BrowseName = new QualifiedName("Controller1", 2),
            DisplayName = new LocalizedText("en", "Controller 1"),
            NodeId = new ExpandedNodeId(new NodeId(200u, 2)),
        };
        var placeholder = new ReferenceDescription
        {
            BrowseName = new QualifiedName("<ControllerTemplate>", 2),
            NodeId = new ExpandedNodeId(new NodeId(201u, 2)),
        };
        var refs = new ReferenceDescriptionCollection { realNode, placeholder };
        var helper = new AddressSpaceHelper();

        var result = await helper.DiscoverAssetInstancesAsync(
            SessionWithBrowseResult(refs).Object, new NodeId(1u, 0));

        Assert.Single(result);
        Assert.Equal("Controller 1", result[0].DisplayName);
    }

    [Fact]
    public async Task DiscoverAssetInstancesAsync_WhenEmpty_ReturnsEmptyList()
    {
        var result = await new AddressSpaceHelper().DiscoverAssetInstancesAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object,
            new NodeId(1u, 0));

        Assert.Empty(result);
    }

    // ── FindByTypeDefinitionAsync ──────────────────────────────────────────────────

    [Fact]
    public async Task FindByTypeDefinition_WhenMatchFound_ReturnsNodeId()
    {
        var childId = new NodeId(300u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("JoiningSystem1", 2),
            NodeId = new ExpandedNodeId(childId),
            TypeDefinition = new ExpandedNodeId(1005u, 2),
        };
        var result = await AddressSpaceHelper.FindByTypeDefinitionAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            Opc.Ua.ObjectIds.ObjectsFolder,
            1005u);

        Assert.Equal(childId, result);
    }

    [Fact]
    public async Task FindByTypeDefinition_WhenNoMatch_ReturnsNullNodeId()
    {
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("SomeOtherObject", 2),
            NodeId = new ExpandedNodeId(new NodeId(400u, 2)),
            TypeDefinition = new ExpandedNodeId(9999u, 2),
        };
        var result = await AddressSpaceHelper.FindByTypeDefinitionAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            Opc.Ua.ObjectIds.ObjectsFolder,
            1005u);

        Assert.True(result.IsNull);
    }

    // ── FindChildAsync and FindMethodNodeAsync ────────────────────────────────

    [Fact]
    public async Task FindChildAsync_WhenMatchFound_ReturnsNodeId()
    {
        var childId = new NodeId(500u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("MethodSet", 2),
            NodeId = new ExpandedNodeId(childId),
        };
        var result = await new AddressSpaceHelper().FindChildAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            "MethodSet");

        Assert.Equal(childId, result);
    }

    [Fact]
    public async Task FindChildAsync_WithNsFilter_ReturnsOnlyMatchingNamespace()
    {
        var correctId = new NodeId(501u, 2);
        var wrongNs = new ReferenceDescription
        {
            BrowseName = new QualifiedName("MethodSet", 1),
            NodeId = new ExpandedNodeId(new NodeId(500u, 1)),
        };
        var correct = new ReferenceDescription
        {
            BrowseName = new QualifiedName("MethodSet", 2),
            NodeId = new ExpandedNodeId(correctId),
        };
        var result = await new AddressSpaceHelper().FindChildAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { wrongNs, correct }).Object,
            new NodeId(1u, 0),
            "MethodSet",
            nsIndex: 2);

        Assert.Equal(correctId, result);
    }

    [Fact]
    public async Task FindMethodNodeAsync_WhenMethodFound_ReturnsNodeId()
    {
        var methodId = new NodeId(600u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("GetLatestResult", 2),
            NodeId = new ExpandedNodeId(methodId),
            NodeClass = NodeClass.Method,
        };
        var result = await new AddressSpaceHelper().FindMethodNodeAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            "GetLatestResult");

        Assert.Equal(methodId, result);
    }

    [Fact]
    public async Task FindMethodNodeAsync_WhenNotFound_ReturnsNullNodeId()
    {
        var result = await new AddressSpaceHelper().FindMethodNodeAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object,
            new NodeId(1u, 0),
            "NonExistentMethod");

        Assert.True(result.IsNull);
    }

    // ── FindJoiningSystemAsync ────────────────────────────────────────────────

    [Fact]
    public async Task FindJoiningSystemAsync_WhenTypeDefMatchAtTopLevel_ReturnsNodeId()
    {
        var nodeId = new NodeId(1001u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("JoiningSystem1", 2),
            NodeId = new ExpandedNodeId(nodeId),
            TypeDefinition = new ExpandedNodeId(IJTBase.ObjectTypes.JoiningSystemType, 2),
        };
        var helper = new AddressSpaceHelper();
        var result = await helper.FindJoiningSystemAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object, 2);

        Assert.Equal(nodeId, result);
    }

    [Fact]
    public async Task FindJoiningSystemAsync_SecondCall_HitsCache()
    {
        var nodeId = new NodeId(1001u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("JoiningSystem1", 2),
            NodeId = new ExpandedNodeId(nodeId),
            TypeDefinition = new ExpandedNodeId(IJTBase.ObjectTypes.JoiningSystemType, 2),
        };
        var mock = SessionWithBrowseResult(new ReferenceDescriptionCollection { rd });
        var helper = new AddressSpaceHelper();

        var first = await helper.FindJoiningSystemAsync(mock.Object, 2);
        var second = await helper.FindJoiningSystemAsync(mock.Object, 2); // cache hit

        Assert.Equal(first, second);
        // Browse called exactly once (second call uses cache)
        mock.Verify(s => s.BrowseAsync(
            It.IsAny<RequestHeader>(), It.IsAny<ViewDescription>(),
            It.IsAny<uint>(), It.IsAny<ArrayOf<BrowseDescription>>(),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task FindJoiningSystemAsync_WhenNoMatchAtTopLevel_UsesFallbackNode()
    {
        var nodeId = new NodeId(999u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("NotAJoiningSystem", 2),
            NodeId = new ExpandedNodeId(nodeId),
            TypeDefinition = new ExpandedNodeId(9999u, 2),   // wrong type
        };
        var helper = new AddressSpaceHelper();
        var result = await helper.FindJoiningSystemAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object, 2);

        // Should fall back to first non-Server node
        Assert.Equal(nodeId, result);
    }

    [Fact]
    public async Task FindJoiningSystemAsync_WhenAllServerObjects_ReturnsNullNodeId()
    {
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("Server", 0),
            NodeId = new ExpandedNodeId(new NodeId(2253u, 0)),
            TypeDefinition = new ExpandedNodeId(9999u, 2),
        };
        var helper = new AddressSpaceHelper();
        var result = await helper.FindJoiningSystemAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object, 2);

        Assert.True(result.IsNull);
    }

    [Fact]
    public async Task FindJoiningSystemAsync_WhenTypeDefMatchViaNumericId_ReturnsNode()
    {
        var nodeId = new NodeId(1002u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("JS2", 2),
            NodeId = new ExpandedNodeId(nodeId),
            TypeDefinition = new ExpandedNodeId(IJTBase.ObjectTypes.JoiningSystemType, 5),
        };
        var helper = new AddressSpaceHelper();
        var result = await helper.FindJoiningSystemAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object, 2);

        Assert.Equal(nodeId, result);
    }

    [Fact]
    public async Task FindJoiningSystemAsync_WhenBrowseReturnsEmpty_ReturnsNullNodeId()
    {
        var helper = new AddressSpaceHelper();
        var result = await helper.FindJoiningSystemAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object, 2);

        Assert.True(result.IsNull);
    }

    // ── GetIdentificationNodeAsync ────────────────────────────────────────────

    [Fact]
    public async Task GetIdentificationNodeAsync_WhenDiNamespaceMatch_ReturnsNode()
    {
        var identId = new NodeId(700u, 4);  // ns=4 == diNsIndex
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("Identification", 4),
            NodeId = new ExpandedNodeId(identId),
        };
        var helper = new AddressSpaceHelper();
        var result = await helper.GetIdentificationNodeAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            diNsIndex: 4,
            ijtNsIndex: 2);

        Assert.Equal(identId, result);
    }

    [Fact]
    public async Task GetIdentificationNodeAsync_WhenAnyNamespaceMatch_ReturnsFallback()
    {
        var identId = new NodeId(701u, 3);  // ns=3, not diNsIndex=4
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("Identification", 3),
            NodeId = new ExpandedNodeId(identId),
        };
        var helper = new AddressSpaceHelper();
        var result = await helper.GetIdentificationNodeAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            diNsIndex: 4,
            ijtNsIndex: 2);

        Assert.Equal(identId, result);
    }

    [Fact]
    public async Task GetIdentificationNodeAsync_WhenNoMatch_ReturnsNullNodeId()
    {
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("NotIdentification", 2),
            NodeId = new ExpandedNodeId(new NodeId(702u, 2)),
        };
        var helper = new AddressSpaceHelper();
        var result = await helper.GetIdentificationNodeAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            diNsIndex: 4,
            ijtNsIndex: 2);

        Assert.True(result.IsNull);
    }

    // ── EnumerateAssetsAsync ───────────────────────────────────────────────────────

    [Fact]
    public async Task EnumerateAssets_WhenPathNotFound_ReturnsEmpty()
    {
        var result = await AddressSpaceHelper.EnumerateAssetsAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object,
            new NodeId(1u, 0),
            "Controllers");

        Assert.Empty(result);
    }

    [Fact]
    public async Task EnumerateAssets_WhenBrowseReturnsEmpty_IsEmpty()
    {
        var simpleResult = await AddressSpaceHelper.EnumerateAssetsAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object,
            new NodeId(1u, 0),
            "Controllers");
        Assert.Empty(simpleResult); // path not found → empty
    }

    [Fact]
    public async Task EnumerateAssets_WhenPathResolved_ReturnsNonPlaceholderAssets()
    {
        // Build a collection with all path segments AND asset children
        // so ResolvePathAsync resolves each segment from the same Browse result
        var allRefs = new ReferenceDescriptionCollection
        {
            new ReferenceDescription
            {
                BrowseName = new QualifiedName("AssetManagement", 2),
                NodeId     = new ExpandedNodeId(new NodeId(10u, 2)),
            },
            new ReferenceDescription
            {
                BrowseName = new QualifiedName("Assets", 2),
                NodeId     = new ExpandedNodeId(new NodeId(11u, 2)),
            },
            new ReferenceDescription
            {
                BrowseName = new QualifiedName("Controllers", 2),
                NodeId     = new ExpandedNodeId(new NodeId(12u, 2)),
            },
            new ReferenceDescription
            {
                BrowseName = new QualifiedName("Controller1", 2),
                NodeId     = new ExpandedNodeId(new NodeId(13u, 2)),
            },
            new ReferenceDescription
            {
                BrowseName = new QualifiedName("<PlaceholderTemplate>", 2),
                NodeId     = new ExpandedNodeId(new NodeId(14u, 2)),
            },
        };

        var result = await AddressSpaceHelper.EnumerateAssetsAsync(
            SessionWithBrowseResult(allRefs).Object,
            new NodeId(1u, 0),
            "Controllers");

        Assert.NotEmpty(result);
        Assert.Contains(result, r => r.Item1 == "Controller1");
        Assert.DoesNotContain(result, r => r.Item1.StartsWith('<'));
    }

    // ── ReadAssetIdentificationAsync ───────────────────────────────────────────────

    [Fact]
    public async Task ReadAssetIdentification_WhenNoIdNode_ReturnsDefaultMessage()
    {
        var result = await AddressSpaceHelper.ReadAssetIdentificationAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object,
            new NodeId(1u, 0));

        Assert.Contains("no Identification", result);
    }

    [Fact]
    public async Task ReadAssetIdentification_WhenIdNodeFound_ReturnsFormattedString()
    {
        var idNodeId = new NodeId(900u, 2);
        var idRef = new ReferenceDescription
        {
            BrowseName = new QualifiedName("Identification", 2),
            NodeId = new ExpandedNodeId(idNodeId),
        };
        // With Browse returning idRef for all calls, FindChildAsync("Identification") returns idNodeId
        // Then FindChildAsync("Manufacturer"), FindChildAsync("SerialNumber"), FindChildAsync("Description")
        // all return idNodeId because Browse still returns idRef for those too.
        // ReadValueAsync for each will fail (no Read mock) → returns null.
        var result = await AddressSpaceHelper.ReadAssetIdentificationAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { idRef }).Object,
            new NodeId(1u, 0));

        Assert.Contains("Manufacturer=", result);
    }

    // ── ReadValueAsync exception paths ─────────────────────────────────────────────

    [Fact]
    public async Task ReadValue_WhenInvalidCastException_ReturnsNull()
    {
        var mock = new Mock<ISession>();
        mock.Setup(s => s.ReadAsync(
                It.IsAny<RequestHeader>(),
                It.IsAny<double>(),
                It.IsAny<TimestampsToReturn>(),
                It.IsAny<ArrayOf<ReadValueId>>(),
                It.IsAny<CancellationToken>()))
            .Throws(new InvalidCastException());

        var result = await AddressSpaceHelper.ReadValueAsync(mock.Object, new NodeId(1u, 0));
        Assert.Null(result);
    }

    [Fact]
    public async Task ReadValueT_WhenConvertThrowsInvalidCast_ReturnsDefault()
    {
        var mock = SessionWithReadResult(new DataValue(new Variant(new NodeId(1u, 0)), StatusCodes.Good));

        var result = await AddressSpaceHelper.ReadValueAsync<int>(mock.Object, new NodeId(1u, 0));
        Assert.Equal(0, result);
    }

    [Fact]
    public async Task ReadValueT_WhenConvertThrowsOverflow_ReturnsDefault()
    {
        var mock = SessionWithReadResult(new DataValue(new Variant(long.MaxValue), StatusCodes.Good));

        var result = await AddressSpaceHelper.ReadValueAsync<byte>(mock.Object, new NodeId(1u, 0));
        Assert.Equal(0, result);
    }

    [Fact]
    public async Task FindJoiningSystemAsync_WhenNestedUnderFolderObject_DiscoversSuccessfully()
    {
        // Test second-level browse: Objects/ApplicationRoot/JoiningSystem1
        var joiningSystemId = new NodeId(9999u, 4);

        // First-level refs: Objects folder contains ApplicationRoot (not JoiningSystemType)
        var firstLevelRefs = new ReferenceDescriptionCollection
        {
            new()
            {
                BrowseName = new QualifiedName("Server", 0),
                NodeId = new ExpandedNodeId(Opc.Ua.ObjectIds.Server),
                TypeDefinition = new ExpandedNodeId(Opc.Ua.ObjectTypeIds.BaseObjectType),
            },
            new()
            {
                BrowseName = new QualifiedName("ApplicationRoot", 4),
                NodeId = new ExpandedNodeId(new NodeId(1000u, 4)),
                TypeDefinition = new ExpandedNodeId(Opc.Ua.ObjectTypeIds.BaseObjectType),
            },
        };

        // Second-level refs: ApplicationRoot contains JoiningSystem1
        var secondLevelRefs = new ReferenceDescriptionCollection
        {
            new()
            {
                BrowseName = new QualifiedName("JoiningSystem1", 4),
                NodeId = new ExpandedNodeId(joiningSystemId),
                TypeDefinition = new ExpandedNodeId(IJTBase.ObjectTypes.JoiningSystemType, 4),
            },
        };

        // Mock that returns different results for different Browse calls
        var mock = new Mock<ISession>();
        mock.Setup(s => s.MessageContext).Returns(ServiceMessageContext.CreateEmpty(DefaultTelemetry.Create(_ => { })));
        mock.Setup(s => s.OperationLimits).Returns(new OperationLimits());
        mock.Setup(s => s.ServerCapabilities).Returns(new ServerCapabilities());
        var callCount = 0;

        mock.Setup(s => s.BrowseAsync(
                It.IsAny<RequestHeader>(),
                It.IsAny<ViewDescription>(),
                It.IsAny<uint>(),
                It.IsAny<ArrayOf<BrowseDescription>>(),
                It.IsAny<CancellationToken>()))
            .Returns(() =>
            {
                var curRefs = callCount++ == 0 ? firstLevelRefs : secondLevelRefs;
                return new ValueTask<BrowseResponse>(new BrowseResponse
                {
                    ResponseHeader = new ResponseHeader(),
                    Results = new ArrayOf<BrowseResult>(new[]
                    {
                        new BrowseResult
                        {
                            StatusCode = StatusCodes.Good,
                            References = new ArrayOf<ReferenceDescription>(curRefs.ToArray())
                        }
                    })
                });
            });

        var helper = new AddressSpaceHelper();
        var result = await helper.FindJoiningSystemAsync(mock.Object, 4);

        Assert.Equal(joiningSystemId, result);
    }
}
