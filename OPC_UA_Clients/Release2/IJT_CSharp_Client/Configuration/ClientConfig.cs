namespace IJT_CSharp_Client.Configuration;

/// <summary>
/// Connection and behaviour settings for the IJT OPC UA client.
/// Override defaults via constructor or use the <see cref="FromEnvironment"/> factory.
/// </summary>
public sealed class ClientConfig
{
    /// <summary>OPC UA server endpoint URL.</summary>
    public string ServerUrl { get; init; } = "opc.tcp://localhost:40451";

    /// <summary>Application display name sent to the server.</summary>
    public string ApplicationName { get; init; } = "IJT CSharp Client";

    /// <summary>Session keep-alive timeout in milliseconds.</summary>
    public int SessionTimeoutMs { get; init; } = 60_000;

    /// <summary>Default publishing interval for subscriptions (ms).</summary>
    public int PublishingIntervalMs { get; init; } = 1_000;

    /// <summary>
    /// When true the client auto-accepts server certificates (development only).
    /// Set to false in production and manage the trust store explicitly.
    /// </summary>
    public bool AutoAcceptServerCertificate { get; init; } = false;

    /// <summary>
    /// Reuses endpoint discovery metadata for repeated connections to the same URL.
    /// Keep disabled for production clients that must observe endpoint changes immediately;
    /// enable for live test suites that open many short-lived sessions against one stable server.
    /// </summary>
    public bool CacheEndpointDiscovery { get; init; } = false;

    /// <summary>
    /// Reads overrides from well-known environment variables so the client can be
    /// configured without recompiling:
    /// <list type="bullet">
    ///   <item>IJT_SERVER_URL  — OPC UA server endpoint URL</item>
    ///   <item>IJT_APP_NAME    — application display name sent to the server</item>
    ///   <item>IJT_AUTO_ACCEPT — set to "true" to accept untrusted certificates (dev only)</item>
    ///   <item>IJT_LOG_LEVEL   — e.g. "Debug", "Information", "Warning", "Error"</item>
    /// </list>
    /// </summary>
    public static ClientConfig FromEnvironment() => new()
    {
        ServerUrl = Environment.GetEnvironmentVariable("IJT_SERVER_URL") ?? "opc.tcp://localhost:40451",
        ApplicationName = Environment.GetEnvironmentVariable("IJT_APP_NAME") ?? "IJT CSharp Client",
        AutoAcceptServerCertificate = string.Equals(
            Environment.GetEnvironmentVariable("IJT_AUTO_ACCEPT"), "true",
            StringComparison.OrdinalIgnoreCase),
    };
}
