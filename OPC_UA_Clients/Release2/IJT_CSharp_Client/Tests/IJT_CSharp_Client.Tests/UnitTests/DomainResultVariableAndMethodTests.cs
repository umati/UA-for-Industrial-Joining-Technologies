#nullable enable

using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Domain.Events;
using IJT_CSharp_Client.Domain.Results;
using IJTBase;
using MachineryResult;
using Moq;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.UnitTests;

/// <summary>
/// Slice 2B and Slice 2C Acceptance Tests:
/// 1. Slice 2B: Variable / Polling Fallback Path Decoupling (IResultVariableReceiver, OnResultVariableChanged).
/// 2. Slice 2C: Method Queries & Historical Results Path Decoupling (IResultMethodClient, MethodResultResponse).
/// </summary>
public sealed class DomainResultVariableAndMethodTests
{
    private static Mock<IJoiningSystem> CreateSessionMock(NodeId? rmNodeId = null, NodeId? methodId = null)
    {
        var mock = new Mock<IJoiningSystem>();
        var validRm = rmNodeId ?? new NodeId(8002u, (ushort)2);
        var validMeth = methodId ?? new NodeId(8003u, (ushort)2);

        mock.Setup(s => s.NodeId).Returns(new NodeId(8001u, (ushort)2));
        mock.Setup(s => s.BrowseChild(It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(validRm);
        mock.Setup(s => s.BrowseMethod(It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .Returns(validMeth);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(validRm);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(validMeth);
        return mock;
    }

    // ── Slice 2B: Variable Path Decoupling ────────────────────────────────────

    [Fact]
    public void ProcessResultVariableValue_ValidResult_FiresOnResultVariableChangedWithDomainEnvelope()
    {
        var mock = CreateSessionMock();
        using var rm = new ResultManagement(mock.Object);

        DomainResultEnvelope? received = null;
        rm.OnResultVariableChanged += (_, envelope) => received = envelope;

        var testTime = new DateTime(2026, 10, 7, 16, 0, 0, DateTimeKind.Utc);
        var rd = new ResultDataType
        {
            ResultMetaData = new JoiningResultMetaDataType
            {
                ResultId = "VAR-RES-100",
                Name = "Variable Tightening",
                SequenceNumber = 99,
                CreationTime = testTime,
                ResultEvaluation = ResultEvaluationEnum.OK
            }
        };

        var processed = rm.ProcessResultVariableValue(
            new DataValue(new Variant(new ExtensionObject(rd)), StatusCodes.Good),
            _ => { });

        Assert.True(processed);
        Assert.NotNull(received);
        Assert.Equal("VAR-RES-100", received!.ResultId);
        Assert.Equal("Variable Tightening", received.Name);
        Assert.Equal(99L, received.SequenceNumber);
        Assert.Equal("OK", received.ResultEvaluation);
        Assert.Equal(testTime, received.CreationTime);
    }

    [Fact]
    public void ProcessResultVariableValue_NullOrPlaceholder_DoesNotFireEvent()
    {
        var mock = CreateSessionMock();
        using var rm = new ResultManagement(mock.Object);

        DomainResultEnvelope? received = null;
        rm.OnResultVariableChanged += (_, envelope) => received = envelope;

        // 1. Null value
        var processedNull = rm.ProcessResultVariableValue(new DataValue(Variant.Null, StatusCodes.Good), _ => { });
        Assert.False(processedNull);
        Assert.Null(received);

        // 2. Empty placeholder
        var placeholderRd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "" }
        };
        var processedPlaceholder = rm.ProcessResultVariableValue(
            new DataValue(new Variant(new ExtensionObject(placeholderRd)), StatusCodes.Good),
            _ => { });
        Assert.False(processedPlaceholder);
        Assert.Null(received);
    }

    // ── Slice 2C: Method Queries & Historical Results ─────────────────────────

    [Fact]
    public void GetLatestResult_Success_ReturnsTypedMethodResultResponse()
    {
        var mock = CreateSessionMock();
        var rd = new ResultDataType
        {
            ResultMetaData = new JoiningResultMetaDataType
            {
                ResultId = "METHOD-RES-001",
                Name = "Latest Result Method",
                SequenceNumber = 50,
                ResultEvaluation = ResultEvaluationEnum.OK
            }
        };

        mock.Setup(s => s.CallMethod(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object> { 42u, new ExtensionObject(rd), 0 });

        using var rm = new ResultManagement(mock.Object);
        var response = rm.GetLatestResult(5000);

        Assert.True(response.IsSuccess);
        Assert.Equal(42u, response.ResultHandle);
        Assert.Equal(0, response.ServerErrorCode);
        Assert.Null(response.ErrorMessage);
        Assert.NotNull(response.Result);
        Assert.Equal("METHOD-RES-001", response.Result!.ResultId);
        Assert.Equal("Latest Result Method", response.Result.Name);
        Assert.Equal(50L, response.Result.SequenceNumber);
    }

    [Fact]
    public void GetLatestResult_ServerError_ReturnsDistinctServerErrorCode()
    {
        var mock = CreateSessionMock();
        mock.Setup(s => s.CallMethod(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object> { 12u, null!, 105 }); // Error 105 returned by server

        using var rm = new ResultManagement(mock.Object);
        var response = rm.GetLatestResult(5000);

        Assert.False(response.IsSuccess);
        Assert.Equal(12u, response.ResultHandle);
        Assert.Equal(105, response.ServerErrorCode);
        Assert.Null(response.Result);
        Assert.NotNull(response.ErrorMessage);
        Assert.Contains("105", response.ErrorMessage);
    }

    [Fact]
    public void GetResultById_TransportFailure_ReturnsDistinctTransportError()
    {
        var mock = CreateSessionMock();
        mock.Setup(s => s.CallMethod(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new ServiceResultException(StatusCodes.BadTimeout));

        using var rm = new ResultManagement(mock.Object);
        var response = rm.GetResultById("QUERY-RES-999", 5000);

        Assert.False(response.IsSuccess);
        Assert.Equal(0u, response.ResultHandle);
        Assert.Equal(unchecked((int)StatusCodes.BadTimeout.Code), response.ServerErrorCode);
        Assert.Null(response.Result);
        Assert.NotNull(response.ErrorMessage);
        Assert.Contains("BadTimeout", response.ErrorMessage);
    }

    [Fact]
    public void GetResultById_Success_ReturnsTypedMethodResultResponse()
    {
        var mock = CreateSessionMock();
        var rd = new ResultDataType
        {
            ResultMetaData = new JoiningResultMetaDataType
            {
                ResultId = "QUERY-RES-777",
                Name = "Queried By Id",
                SequenceNumber = 77,
                ResultEvaluation = ResultEvaluationEnum.OK
            }
        };

        mock.Setup(s => s.CallMethod(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object> { 101u, new ExtensionObject(rd), 0 });

        using var rm = new ResultManagement(mock.Object);
        var response = rm.GetResultById("QUERY-RES-777", 5000);

        Assert.True(response.IsSuccess);
        Assert.Equal(101u, response.ResultHandle);
        Assert.Equal(0, response.ServerErrorCode);
        Assert.NotNull(response.Result);
        Assert.Equal("QUERY-RES-777", response.Result!.ResultId);
        Assert.Equal("Queried By Id", response.Result.Name);
    }
}
