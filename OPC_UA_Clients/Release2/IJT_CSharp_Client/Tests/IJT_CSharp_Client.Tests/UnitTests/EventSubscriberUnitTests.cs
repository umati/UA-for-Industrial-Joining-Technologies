#nullable enable

using IJT_CSharp_Client.Client;
using Xunit;

namespace IJT_CSharp_Client.Tests.UnitTests;

/// <summary>
/// Unit tests for <see cref="EventSubscriber"/> — menu items 1, 2.
/// These tests exercise the .NET event wiring, subscription guard, and
/// unsubscribe clean-up paths without requiring a live OPC UA server.
///
/// Note: Subscribe() internally calls ISession.AddSubscription() and
/// Subscription.Create() which communicate with the OPC UA server stack.
/// Tests covering the subscription lifecycle end-to-end are in
/// <see cref="LiveIntegrationTests"/> (server-required tests).
/// Here we test the guards and event contract exposed through IIjtSession.
///
/// Covered operations:
///   1  Subscribe to Result + System events
///   2  Unsubscribe
/// </summary>
public sealed class EventSubscriberUnitTests
{
    // ── 2. Unsubscribe (safe without prior subscribe) ─────────────────────────

    [Fact]
    public void Unsubscribe_WithoutPriorSubscribe_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        using var sub = new EventSubscriber(session.Object);

        var ex = Record.Exception(() => sub.Unsubscribe());

        Assert.Null(ex);
    }

    [Fact]
    public void Unsubscribe_CalledMultipleTimes_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        using var sub = new EventSubscriber(session.Object);

        sub.Unsubscribe();
        var ex = Record.Exception(() => sub.Unsubscribe());

        Assert.Null(ex);
    }

    // ── Event routing ─────────────────────────────────────────────────────────

    [Fact]
    public void OnResultReady_CanAttachAndDetachHandlerWithoutThrow()
    {
        var session = MockSessionBuilder.Create();
        using var sub = new EventSubscriber(session.Object);

        EventHandler<EventSubscriber.ResultReadyEventArgs>? handler =
            (_, _) => { /* no-op */ };

        sub.OnResultReady += handler;
        var ex = Record.Exception(() => sub.OnResultReady -= handler);

        Assert.Null(ex);
    }

    [Fact]
    public void OnJoiningSystemEvent_CanAttachAndDetachHandlerWithoutThrow()
    {
        var session = MockSessionBuilder.Create();
        using var sub = new EventSubscriber(session.Object);

        EventHandler<EventSubscriber.JoiningSystemEventArgs>? handler =
            (_, _) => { /* no-op */ };

        sub.OnJoiningSystemEvent += handler;
        var ex = Record.Exception(() => sub.OnJoiningSystemEvent -= handler);

        Assert.Null(ex);
    }

    // ── Dispose ───────────────────────────────────────────────────────────────

    [Fact]
    public void Dispose_WithNoSubscription_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        var ex = Record.Exception(() =>
        {
            using var sub = new EventSubscriber(session.Object);
        });

        Assert.Null(ex);
    }

    // ── EventArgs immutability ────────────────────────────────────────────────

    [Fact]
    public void ResultReadyEventArgs_InitProperties_AreAccessible()
    {
        var now = DateTime.UtcNow;
        var args = new EventSubscriber.ResultReadyEventArgs
        {
            ResultId = "R-001",
            Classification = "OK",
            Name = "TorqueProgram_A",
            SequenceNumber = 42,
            AssemblyType = "M8",
            OverallStatus = "OK",
            EventTypeName = "JoiningSystemResultReadyEventType",
            EventTime = now,
            Result = null,
            AllFields = [],
        };

        Assert.Equal("R-001", args.ResultId);
        Assert.Equal("OK", args.Classification);
        Assert.Equal("TorqueProgram_A", args.Name);
        Assert.Equal(42, args.SequenceNumber);
        Assert.Equal("M8", args.AssemblyType);
        Assert.Equal("OK", args.OverallStatus);
        Assert.Equal("JoiningSystemResultReadyEventType", args.EventTypeName);
        Assert.Equal(now, args.EventTime);
        Assert.Null(args.Result);
        Assert.Empty(args.AllFields);
    }

    [Fact]
    public void JoiningSystemEventArgs_InitProperties_AreAccessible()
    {
        var now = DateTime.UtcNow;
        var args = new EventSubscriber.JoiningSystemEventArgs
        {
            EventCode = "1001",
            EventText = "Tool ready",
            JoiningTechnology = "Tightening",
            EventTime = now,
            AssociatedEntities = [],
            ReportedValues = [],
        };

        Assert.Equal("1001", args.EventCode);
        Assert.Equal("Tool ready", args.EventText);
        Assert.Equal("Tightening", args.JoiningTechnology);
        Assert.Equal(now, args.EventTime);
        Assert.Empty(args.AssociatedEntities);
        Assert.Empty(args.ReportedValues);
    }

    [Fact]
    public void ResultReadyEventArgs_WithNullOptionalFields_DoesNotThrow()
    {
        var args = new EventSubscriber.ResultReadyEventArgs
        {
            EventTypeName = "",
            EventTime = DateTime.UtcNow,
        };

        // Optional fields are null — accessing them should not throw
        Assert.Null(args.ResultId);
        Assert.Null(args.Classification);
        Assert.Null(args.Name);
        Assert.Null(args.AssemblyType);
        Assert.Null(args.OverallStatus);
        Assert.Null(args.Result);
    }
}
