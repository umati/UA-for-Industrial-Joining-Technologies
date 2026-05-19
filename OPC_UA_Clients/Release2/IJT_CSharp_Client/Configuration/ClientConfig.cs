using Opc.Ua;

namespace IJT_CSharp_Client.Configuration;

/// <summary>User identity type used when activating an OPC UA session.</summary>
public enum UserIdentityKind
{
    Anonymous,
    UserName,
    X509,
}

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
    /// Asks endpoint discovery to prefer secure endpoints when no exact policy/mode
    /// was requested.
    /// </summary>
    public bool UseSecurityPolicyForEndpointDiscovery { get; init; } = false;

    /// <summary>Exact endpoint security policy URI to select, or null for default SDK selection.</summary>
    public string? SecurityPolicyUri { get; init; }

    /// <summary>Exact endpoint message security mode to select, or null for default SDK selection.</summary>
    public MessageSecurityMode? MessageSecurityMode { get; init; }

    /// <summary>User identity kind to send during ActivateSession.</summary>
    public UserIdentityKind UserIdentityKind { get; init; } = UserIdentityKind.Anonymous;

    /// <summary>UserName identity user name.</summary>
    public string? UserName { get; init; }

    /// <summary>UserName identity password.</summary>
    public string? Password { get; init; }

    /// <summary>X509 user identity certificate path. Supports PFX/P12 and PEM/DER certificate files.</summary>
    public string? X509IdentityCertificatePath { get; init; }

    /// <summary>Optional PEM private-key path for an X509 user identity certificate.</summary>
    public string? X509IdentityPrivateKeyPath { get; init; }

    /// <summary>Optional override for the OPC UA SDK PKI root used by this client instance.</summary>
    public string? PkiRootPath { get; init; }

    /// <summary>
    /// Reads overrides from well-known environment variables so the client can be
    /// configured without recompiling:
    /// <list type="bullet">
    ///   <item>IJT_SERVER_URL  — OPC UA server endpoint URL</item>
    ///   <item>IJT_APP_NAME    — application display name sent to the server</item>
    ///   <item>IJT_AUTO_ACCEPT — set to "true" to accept untrusted certificates (dev only)</item>
    ///   <item>IJT_LOG_LEVEL   — e.g. "Debug", "Information", "Warning", "Error"</item>
    ///   <item>IJT_USE_SECURITY_FOR_DISCOVERY — set to "true" to prefer secure endpoints</item>
    ///   <item>IJT_SECURITY_POLICY_URI — exact endpoint security policy URI</item>
    ///   <item>IJT_MESSAGE_SECURITY_MODE — None, Sign, or SignAndEncrypt</item>
    ///   <item>IJT_USER_IDENTITY_KIND — Anonymous, UserName, or X509</item>
    ///   <item>IJT_USERNAME / IJT_PASSWORD — UserName identity credentials</item>
    ///   <item>IJT_X509_IDENTITY_CERT / IJT_X509_IDENTITY_KEY — X509 user identity material</item>
    ///   <item>IJT_PKI_ROOT — client PKI root directory</item>
    /// </list>
    /// </summary>
    public static ClientConfig FromEnvironment() => new()
    {
        ServerUrl = Environment.GetEnvironmentVariable("IJT_SERVER_URL") ?? "opc.tcp://localhost:40451",
        ApplicationName = Environment.GetEnvironmentVariable("IJT_APP_NAME") ?? "IJT CSharp Client",
        AutoAcceptServerCertificate = string.Equals(
            Environment.GetEnvironmentVariable("IJT_AUTO_ACCEPT"), "true",
            StringComparison.OrdinalIgnoreCase),
        UseSecurityPolicyForEndpointDiscovery = ParseBool("IJT_USE_SECURITY_FOR_DISCOVERY"),
        SecurityPolicyUri = EmptyToNull(Environment.GetEnvironmentVariable("IJT_SECURITY_POLICY_URI")),
        MessageSecurityMode = ParseMessageSecurityMode(Environment.GetEnvironmentVariable("IJT_MESSAGE_SECURITY_MODE")),
        UserIdentityKind = ParseUserIdentityKind(Environment.GetEnvironmentVariable("IJT_USER_IDENTITY_KIND")),
        UserName = EmptyToNull(Environment.GetEnvironmentVariable("IJT_USERNAME")),
        Password = EmptyToNull(Environment.GetEnvironmentVariable("IJT_PASSWORD")),
        X509IdentityCertificatePath = EmptyToNull(Environment.GetEnvironmentVariable("IJT_X509_IDENTITY_CERT")),
        X509IdentityPrivateKeyPath = EmptyToNull(Environment.GetEnvironmentVariable("IJT_X509_IDENTITY_KEY")),
        PkiRootPath = EmptyToNull(Environment.GetEnvironmentVariable("IJT_PKI_ROOT")),
    };

    private static bool ParseBool(string name)
        => string.Equals(Environment.GetEnvironmentVariable(name), "true", StringComparison.OrdinalIgnoreCase);

    private static string? EmptyToNull(string? value)
        => string.IsNullOrWhiteSpace(value) ? null : value;

    private static MessageSecurityMode? ParseMessageSecurityMode(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return null;

        return Enum.TryParse<MessageSecurityMode>(value, ignoreCase: true, out var parsed)
            ? parsed
            : throw new InvalidOperationException($"Invalid IJT_MESSAGE_SECURITY_MODE value: {value}");
    }

    private static UserIdentityKind ParseUserIdentityKind(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return UserIdentityKind.Anonymous;

        return Enum.TryParse<UserIdentityKind>(value, ignoreCase: true, out var parsed)
            ? parsed
            : throw new InvalidOperationException($"Invalid IJT_USER_IDENTITY_KIND value: {value}");
    }
}
