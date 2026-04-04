#nullable enable

using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Helpers;
using Moq;
using Opc.Ua;
using Opc.Ua.Client;
using Xunit;

namespace IJT_CSharp_Client.Tests.Client;

/// <summary>
/// Unit tests for <see cref="EventSubscriber"/>.
/// Tests focus on lifecycle management and event-args data structures.
/// Actual OPC UA event notification tests require a live server.
/// </summary>
public sealed class EventSubscriberTests
{
    private static Mock<IIjtSession> CreateMock()
    {
        var mock = new Mock<IIjtSession>();
        mock.Setup(s => s.IjtBaseNsIdx).Returns((ushort)2);
        mock.Setup(s => s.MachineryResultNsIdx).Returns((ushort)3);
        mock.Setup(s => s.Config).Returns(new global::IJT_CSharp_Client.Configuration.ClientConfig());
        return mock;
    }

    // ── Construction ──────────────────────────────────────────────────────────

    [Fact]
    public void Constructor_DoesNotThrow()
    {
        var ex = Record.Exception(() => new EventSubscriber(CreateMock().Object));
        Assert.Null(ex);
    }

    // ── Unsubscribe ───────────────────────────────────────────────────────────

    [Fact]
    public void Unsubscribe_WhenNotSubscribed_DoesNotThrow()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        var ex  = Record.Exception(() => sut.Unsubscribe());
        Assert.Null(ex);
    }

    [Fact]
    public void Unsubscribe_CalledTwice_DoesNotThrow()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        sut.Unsubscribe();
        var ex = Record.Exception(() => sut.Unsubscribe());
        Assert.Null(ex);
    }

    // ── Dispose ───────────────────────────────────────────────────────────────

    [Fact]
    public void Dispose_WhenNotSubscribed_DoesNotThrow()
    {
        var ex = Record.Exception(() => new EventSubscriber(CreateMock().Object).Dispose());
        Assert.Null(ex);
    }

    // ── Event args types ──────────────────────────────────────────────────────

    [Fact]
    public void ResultReadyEventArgs_PropertiesAreSettable()
    {
        var now  = DateTime.UtcNow;
        var args = new EventSubscriber.ResultReadyEventArgs
        {
            EventTypeName  = "TestType",
            EventTime      = now,
            ResultId       = "RES-1",
            Classification = "OK",
            Name           = "TestProgram",
            SequenceNumber = 42,
            AssemblyType   = "type-A",
            OverallStatus  = "OK",
        };

        Assert.Equal("TestType", args.EventTypeName);
        Assert.Equal(now,        args.EventTime);
        Assert.Equal("RES-1",    args.ResultId);
        Assert.Equal("OK",       args.Classification);
        Assert.Equal("TestProgram", args.Name);
        Assert.Equal(42,         args.SequenceNumber);
    }

    [Fact]
    public void ResultReadyEventArgs_AllFields_DefaultsToEmptyList()
    {
        var args = new EventSubscriber.ResultReadyEventArgs();
        Assert.Empty(args.AllFields);
        Assert.Equal("", args.EventTypeName);
    }

    [Fact]
    public void JoiningSystemEventArgs_PropertiesAreSettable()
    {
        var now  = DateTime.UtcNow;
        var args = new EventSubscriber.JoiningSystemEventArgs
        {
            EventCode         = "CODE-1",
            EventText         = "Message text",
            JoiningTechnology = "Tightening",
            EventTime         = now,
        };

        Assert.Equal("CODE-1",       args.EventCode);
        Assert.Equal("Message text", args.EventText);
        Assert.Equal("Tightening",   args.JoiningTechnology);
        Assert.Equal(now,            args.EventTime);
    }

    [Fact]
    public void JoiningSystemEventArgs_AllFields_DefaultsToEmptyList()
    {
        var args = new EventSubscriber.JoiningSystemEventArgs();
        Assert.Empty(args.AllFields);
    }

    // ── Event wire-up ─────────────────────────────────────────────────────────

    [Fact]
    public void OnResultReady_EventCanBeSubscribed_AndUnsubscribed()
    {
        var sut     = new EventSubscriber(CreateMock().Object);
        var handler = new EventHandler<EventSubscriber.ResultReadyEventArgs>((_, _) => { });

        sut.OnResultReady += handler;
        sut.OnResultReady -= handler;

        var ex = Record.Exception(() => sut.Dispose());
        Assert.Null(ex);
    }

    [Fact]
    public void OnJoiningSystemEvent_EventCanBeSubscribed_AndUnsubscribed()
    {
        var sut     = new EventSubscriber(CreateMock().Object);
        var handler = new EventHandler<EventSubscriber.JoiningSystemEventArgs>((_, _) => { });

        sut.OnJoiningSystemEvent += handler;
        sut.OnJoiningSystemEvent -= handler;

        var ex = Record.Exception(() => sut.Dispose());
        Assert.Null(ex);
    }

    [Fact]
    public void Subscribe_WhenAlreadySubscribed_LogsWarningAndReturns()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        // Inject a non-null subscription via reflection to simulate already-subscribed state
        var field = typeof(EventSubscriber).GetField(
            "_eventSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
#pragma warning disable CS0618
        field!.SetValue(sut, new Subscription());
#pragma warning restore CS0618

        // Second call should hit the "already subscribed" guard
        var ex = Record.Exception(() => sut.Subscribe());
        Assert.Null(ex);
    }
}