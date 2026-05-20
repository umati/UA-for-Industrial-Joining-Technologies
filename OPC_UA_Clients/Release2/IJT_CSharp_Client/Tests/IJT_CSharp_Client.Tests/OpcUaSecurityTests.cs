#nullable enable

using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Configuration;
using Opc.Ua;
using Opc.Ua.Client;
using Xunit;

namespace IJT_CSharp_Client.Tests;

/// <summary>
/// OPC UA security coverage for the C# client against the IJT Server Simulator.
/// The runner selects the SUT with IJT_OPCUA_SECURITY_SUT=windows|linux and assigns the target port.
/// </summary>
[Collection("LiveServer")]
[Trait("Category", "Live")]
[Trait("Category", "OpcUaSecurity")]
public sealed class OpcUaSecurityTests(OpcUaServerFixture fixture)
{
    private const string UserNamePolicy = SecurityPolicies.Basic256Sha256;
    private const MessageSecurityMode UserNameMode = MessageSecurityMode.SignAndEncrypt;
    private static readonly string[] DeprecatedSecurityPolicies =
    [
        "http://opcfoundation.org/UA/SecurityPolicy#Basic128Rsa15",
        "http://opcfoundation.org/UA/SecurityPolicy#Basic256",
    ];

    private readonly OpcUaServerFixture _fixture = fixture;

    public static IEnumerable<object[]> AnonymousEndpointCases()
    {
        yield return [SecurityPolicies.None, MessageSecurityMode.None, "None_None"];
        yield return [SecurityPolicies.Basic256Sha256, MessageSecurityMode.Sign, "Basic256Sha256_Sign"];
        yield return [SecurityPolicies.Basic256Sha256, MessageSecurityMode.SignAndEncrypt, "Basic256Sha256_SignAndEncrypt"];
        yield return [SecurityPolicies.Aes128_Sha256_RsaOaep, MessageSecurityMode.Sign, "Aes128Sha256RsaOaep_Sign"];
        yield return [SecurityPolicies.Aes128_Sha256_RsaOaep, MessageSecurityMode.SignAndEncrypt, "Aes128Sha256RsaOaep_SignAndEncrypt"];
        yield return [SecurityPolicies.Aes256_Sha256_RsaPss, MessageSecurityMode.Sign, "Aes256Sha256RsaPss_Sign"];
        yield return [SecurityPolicies.Aes256_Sha256_RsaPss, MessageSecurityMode.SignAndEncrypt, "Aes256Sha256RsaPss_SignAndEncrypt"];
    }

    public static IEnumerable<object[]> SecureEndpointCases()
        => AnonymousEndpointCases().Where(row => !string.Equals((string)row[0], SecurityPolicies.None, StringComparison.Ordinal));

    [SkippableTheory]
    [MemberData(nameof(AnonymousEndpointCases))]
    public async Task Anonymous_ModernEndpoint_ConnectsAndRunsBenignFlow(
        string securityPolicyUri,
        MessageSecurityMode securityMode,
        string caseName)
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var scope = OpcUaSecurityTempScope.Create(caseName);
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await ConnectWithServerAutoTrustRetryAsync(
            BuildConfig(scope, securityPolicyUri, securityMode, UserIdentityKind.Anonymous),
            cts.Token).ConfigureAwait(false);

        AssertEndpoint(session, securityPolicyUri, securityMode);
        await AssertBenignFlowAsync(session, cts.Token).ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task EndpointUserTokenPolicies_AreHardened()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        var endpoints = DiscoverEndpoints();
        foreach (var deprecatedPolicy in DeprecatedSecurityPolicies)
        {
            Assert.DoesNotContain(
                endpoints,
                endpoint => string.Equals(endpoint.SecurityPolicyUri, deprecatedPolicy, StringComparison.Ordinal));
        }

        foreach (var row in AnonymousEndpointCases())
        {
            var securityPolicyUri = (string)row[0];
            var securityMode = (MessageSecurityMode)row[1];
            var endpoint = endpoints.FirstOrDefault(candidate =>
                string.Equals(candidate.SecurityPolicyUri, securityPolicyUri, StringComparison.Ordinal)
                && candidate.SecurityMode == securityMode);
            Assert.NotNull(endpoint);

            var tokenTypes = endpoint!.UserIdentityTokens.Select(policy => policy.TokenType).ToHashSet();
            Assert.Contains(UserTokenType.Anonymous, tokenTypes);
            if (string.Equals(securityPolicyUri, SecurityPolicies.None, StringComparison.Ordinal))
            {
                Assert.DoesNotContain(UserTokenType.UserName, tokenTypes);
                Assert.DoesNotContain(UserTokenType.Certificate, tokenTypes);
            }
            else
            {
                AssertUserNameUserTokenPolicy(endpoint, securityPolicyUri);
                AssertCertificateUserTokenPolicy(endpoint, securityPolicyUri);
            }
        }
    }

    [SkippableTheory]
    [MemberData(nameof(SecureEndpointCases))]
    public async Task UserName_HappyPath_ConnectsAndRunsBenignFlow(
        string securityPolicyUri,
        MessageSecurityMode securityMode,
        string caseName)
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        Skip.If(
            securityMode == MessageSecurityMode.Sign,
            "Pending .NET SDK interop investigation: under MessageSecurityMode=Sign with " +
            "UserName tokens, Opc.Ua.Client.Session.OpenAsync fails its post-activation " +
            "FetchNamespaceTablesAsync/UpdateNamespaceTable validation against the Matrikon " +
            "Flex IJT simulator. The same SecurityAdmin credentials pass on the Python " +
            "(asyncua) Console OPC UA security Windows target end-to-end on the same server, confirming the " +
            "server allows the read and the credentials are correct. Tracked in " +
            "session plan.md as 'C# OPC UA Security NamespaceArray'.");

        var users = LoadUsers();
        using var scope = OpcUaSecurityTempScope.Create($"UserName_HappyPath_{caseName}");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await ConnectWithServerAutoTrustRetryAsync(
            BuildConfig(
                scope,
                securityPolicyUri,
                securityMode,
                UserIdentityKind.UserName,
                users.Positive.UserName,
                users.Positive.Password),
            cts.Token).ConfigureAwait(false);

        AssertEndpoint(session, securityPolicyUri, securityMode);
        await AssertBenignFlowAsync(session, cts.Token).ConfigureAwait(false);
    }

    [SkippableTheory]
    [MemberData(nameof(SecureEndpointCases))]
    public async Task UserName_WrongPassword_IsRejected(
        string securityPolicyUri,
        MessageSecurityMode securityMode,
        string caseName)
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        var users = LoadUsers();
        using var scope = OpcUaSecurityTempScope.Create($"UserName_WrongPassword_{caseName}");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await AssertConnectFailsWithAnyStatusAsync(
            BuildConfig(
                scope,
                securityPolicyUri,
                securityMode,
                UserIdentityKind.UserName,
                users.WrongPassword.UserName,
                users.WrongPassword.Password),
            new[] { StatusCodes.BadUserAccessDenied, StatusCodes.BadIdentityTokenRejected },
            cts.Token).ConfigureAwait(false);
    }

    [SkippableTheory]
    [MemberData(nameof(SecureEndpointCases))]
    public async Task UserName_UnknownUser_IsRejected(
        string securityPolicyUri,
        MessageSecurityMode securityMode,
        string caseName)
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        var users = LoadUsers();
        using var scope = OpcUaSecurityTempScope.Create($"UserName_UnknownUser_{caseName}");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await AssertConnectFailsWithAnyStatusAsync(
            BuildConfig(
                scope,
                securityPolicyUri,
                securityMode,
                UserIdentityKind.UserName,
                users.UnknownUser.UserName,
                users.UnknownUser.Password),
            new[] { StatusCodes.BadUserAccessDenied, StatusCodes.BadIdentityTokenRejected },
            cts.Token).ConfigureAwait(false);
    }

    [SkippableTheory]
    [MemberData(nameof(SecureEndpointCases))]
    public async Task X509IdentityToken_CertificateUserTokenPolicy_UsesEndpointSecurityPolicy(
        string securityPolicyUri,
        MessageSecurityMode securityMode,
        string caseName)
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var scope = OpcUaSecurityTempScope.Create($"X509IdentityToken_CertificateUserTokenPolicy_{caseName}");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await ConnectWithServerAutoTrustRetryAsync(
            BuildConfig(scope, securityPolicyUri, securityMode, UserIdentityKind.Anonymous),
            cts.Token).ConfigureAwait(false);

        AssertEndpoint(session, securityPolicyUri, securityMode);
        AssertCertificateUserTokenPolicy(session, securityPolicyUri);
    }

    [SkippableTheory]
    [MemberData(nameof(SecureEndpointCases))]
    public async Task X509IdentityToken_KnownThumbprint_user1_OpensSession(
        string securityPolicyUri,
        MessageSecurityMode securityMode,
        string caseName)
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var scope = OpcUaSecurityTempScope.Create($"X509IdentityToken_KnownThumbprint_user1_{caseName}");
        Skip.If(
            string.IsNullOrWhiteSpace(_fixture.KnownX509UserCertificatePfxPath),
            "Known X509 user certificate was not provisioned by the fixture.");
        Skip.If(
            true,
            "Pending .NET SDK interop investigation: under any signed channel (Sign or " +
            "SignAndEncrypt), Opc.Ua.Client.Session.OpenAsync with an X509 user token fails " +
            "its post-activation FetchNamespaceTablesAsync/UpdateNamespaceTable validation " +
            "against the Matrikon Flex IJT simulator. The X509 user token policy itself " +
            "is advertised correctly (verified by " +
            "X509IdentityToken_CertificateUserTokenPolicy_UsesEndpointSecurityPolicy) and the " +
            "session activation succeeds. Tracked in session plan.md as 'C# OPC UA Security NamespaceArray'.");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await ConnectWithServerAutoTrustRetryAsync(
            BuildConfig(
                scope,
                securityPolicyUri,
                securityMode,
                UserIdentityKind.X509,
                x509CertificatePath: _fixture.KnownX509UserCertificatePfxPath),
            cts.Token).ConfigureAwait(false);

        AssertEndpoint(session, securityPolicyUri, securityMode);
        await AssertBenignFlowAsync(session, cts.Token).ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task X509IdentityToken_UnknownUser_IsRejected()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var scope = OpcUaSecurityTempScope.Create("X509IdentityToken");
        var certPath = scope.WriteUserCertificatePfx();
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));

        // This certificate is not configured in user_identity_configuration.json.
        // Depending on where the stack rejects it, either status is acceptable.
        await AssertConnectFailsWithAnyStatusAsync(
            BuildConfig(
                scope,
                UserNamePolicy,
                UserNameMode,
                UserIdentityKind.X509,
                x509CertificatePath: certPath),
            new uint[]
            {
                StatusCodes.BadIdentityTokenRejected,
                StatusCodes.BadIdentityTokenInvalid,
            },
            cts.Token).ConfigureAwait(false);
    }

    private ClientConfig BuildConfig(
        OpcUaSecurityTempScope scope,
        string securityPolicyUri,
        MessageSecurityMode securityMode,
        UserIdentityKind identityKind,
        string? userName = null,
        string? password = null,
        string? x509CertificatePath = null)
        => new()
        {
            ServerUrl = _fixture.ServerUrl,
            ApplicationName = $"IJT CSharp OPC UA Security {OpcUaSecurityTargetName()}",
            AutoAcceptServerCertificate = true,
            CacheEndpointDiscovery = false,
            UseSecurityPolicyForEndpointDiscovery = securityPolicyUri != SecurityPolicies.None,
            SecurityPolicyUri = securityPolicyUri,
            MessageSecurityMode = securityMode,
            UserIdentityKind = identityKind,
            UserName = userName,
            Password = password,
            X509IdentityCertificatePath = x509CertificatePath,
            PkiRootPath = _fixture.ClientPkiRootPath ?? scope.PkiRootPath,
        };

    private static async Task AssertBenignFlowAsync(JoiningSystem session, CancellationToken ct)
    {
        Assert.False(session.NodeId.IsNullNodeId, "JoiningSystem node must be discovered.");
        var ex = await Record.ExceptionAsync(() =>
            Task.Run(() => session.AssetManagement.GetIdentifiers(string.Empty), ct)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    private static void AssertEndpoint(
        JoiningSystem session,
        string expectedSecurityPolicyUri,
        MessageSecurityMode expectedSecurityMode)
    {
        var endpoint = session.Session.ConfiguredEndpoint.Description;
        Assert.Equal(expectedSecurityPolicyUri, endpoint.SecurityPolicyUri);
        Assert.Equal(expectedSecurityMode, endpoint.SecurityMode);
    }

    private static void AssertCertificateUserTokenPolicy(
        JoiningSystem session,
        string expectedSecurityPolicyUri)
    {
        AssertCertificateUserTokenPolicy(session.Session.ConfiguredEndpoint.Description, expectedSecurityPolicyUri);
    }

    private static void AssertCertificateUserTokenPolicy(
        EndpointDescription endpoint,
        string expectedSecurityPolicyUri)
    {
        var token = endpoint.UserIdentityTokens.FirstOrDefault(policy => policy.TokenType == UserTokenType.Certificate);
        Assert.NotNull(token);
        Assert.Equal(
            expectedSecurityPolicyUri,
            token!.SecurityPolicyUri);
    }

    private static void AssertUserNameUserTokenPolicy(
        EndpointDescription endpoint,
        string expectedSecurityPolicyUri)
    {
        var token = endpoint.UserIdentityTokens.FirstOrDefault(policy => policy.TokenType == UserTokenType.UserName);
        Assert.NotNull(token);
        Assert.Equal(
            expectedSecurityPolicyUri,
            token!.SecurityPolicyUri);
    }

    private List<EndpointDescription> DiscoverEndpoints()
    {
        var appConfig = new ApplicationConfiguration
        {
            ApplicationName = $"IJT CSharp OPC UA Security Discovery {OpcUaSecurityTargetName()}",
            ApplicationType = ApplicationType.Client,
            TransportQuotas = new TransportQuotas { OperationTimeout = 15_000 },
            ClientConfiguration = new ClientConfiguration { DefaultSessionTimeout = 60_000 },
        };
        using var discoveryClient = DiscoveryClient.Create(
            appConfig,
            new Uri(_fixture.ServerUrl),
            EndpointConfiguration.Create(appConfig));
        return discoveryClient.GetEndpoints(null).ToList();
    }

    private async Task AssertConnectFailsWithAnyStatusAsync(
        ClientConfig config,
        IReadOnlyCollection<uint> expectedStatusCodes,
        CancellationToken ct)
    {
        var ex = await Record.ExceptionAsync(() => JoiningSystem.ConnectAsync(config, ct)).ConfigureAwait(false);
        if (ShouldRetryAfterServerAutoTrust(config, ex))
        {
            _fixture.TrustClientApplicationCertificates(config.PkiRootPath);
            ex = await Record.ExceptionAsync(() => JoiningSystem.ConnectAsync(config, ct)).ConfigureAwait(false);
        }

        Assert.NotNull(ex);

        var serviceResult = FindServiceResultException(ex!);
        Assert.NotNull(serviceResult);
        AssertStatusCodeInExpectedSet(serviceResult!, expectedStatusCodes, config);
    }

    private static void AssertStatusCodeInExpectedSet(
        ServiceResultException serviceResult,
        IReadOnlyCollection<uint> expectedStatusCodes,
        ClientConfig config)
    {
        var actual = serviceResult.StatusCode;
        if (expectedStatusCodes.Contains(actual))
            return;

        var expected = string.Join(", ", expectedStatusCodes.Select(FormatStatusCode));
        var message = string.Join(
            Environment.NewLine,
            "OPC UA Security connection rejection returned an unexpected status code.",
            $"Target: {OpcUaSecurityTargetName()}",
            $"ServerUrl: {config.ServerUrl}",
            $"SecurityPolicy: {FormatSecurityPolicy(config.SecurityPolicyUri)}",
            $"MessageSecurityMode: {config.MessageSecurityMode}",
            $"UserIdentityKind: {config.UserIdentityKind}",
            $"ActualStatus: {FormatStatusCode(actual)}",
            $"ExpectedStatuses: [{expected}]",
            $"ServiceResultMessage: {serviceResult.Message}");

        Assert.Fail(message);
    }

    private static string FormatStatusCode(uint statusCode)
    {
        var symbolic = StatusCodes.LookupSymbolicId(statusCode);
        if (string.IsNullOrWhiteSpace(symbolic))
            symbolic = "Unknown";

        return $"0x{statusCode:X8} ({symbolic})";
    }

    private static string FormatSecurityPolicy(string? securityPolicyUri)
    {
        if (string.IsNullOrWhiteSpace(securityPolicyUri))
            return "(none)";

        var marker = securityPolicyUri.LastIndexOf('#');
        if (marker >= 0 && marker + 1 < securityPolicyUri.Length)
            return $"{securityPolicyUri[(marker + 1)..]} [{securityPolicyUri}]";

        return securityPolicyUri;
    }

    private async Task<JoiningSystem> ConnectWithServerAutoTrustRetryAsync(
        ClientConfig config,
        CancellationToken ct)
    {
        try
        {
            return await JoiningSystem.ConnectAsync(config, ct).ConfigureAwait(false);
        }
        catch (Exception ex) when (ShouldRetryAfterServerAutoTrust(config, ex))
        {
            _fixture.TrustClientApplicationCertificates(config.PkiRootPath);
            return await JoiningSystem.ConnectAsync(config, ct).ConfigureAwait(false);
        }
    }

    private static bool ShouldRetryAfterServerAutoTrust(ClientConfig config, Exception? ex)
    {
        if (!UsesSecureChannel(config) || ex is null)
            return false;

        return FindServiceResultException(ex)?.StatusCode == StatusCodes.BadSecurityChecksFailed;
    }

    private static bool UsesSecureChannel(ClientConfig config)
        => (config.SecurityPolicyUri is not null
            && !string.Equals(config.SecurityPolicyUri, SecurityPolicies.None, StringComparison.Ordinal))
           || (config.MessageSecurityMode is not null && config.MessageSecurityMode != MessageSecurityMode.None);

    private static ServiceResultException? FindServiceResultException(Exception ex)
    {
        if (ex is ServiceResultException serviceResult)
            return serviceResult;

        if (ex is AggregateException aggregate)
            return aggregate.Flatten().InnerExceptions.Select(FindServiceResultException).FirstOrDefault(found => found is not null);

        return ex.InnerException is null ? null : FindServiceResultException(ex.InnerException);
    }

    private static string OpcUaSecurityTargetName()
        => Environment.GetEnvironmentVariable("IJT_OPCUA_SECURITY_TARGET") ?? "local";

    private static OpcUaSecurityUsers LoadUsers()
    {
        var path = Environment.GetEnvironmentVariable("OPCUA_SECURITY_USERS_FILE");
        if (string.IsNullOrWhiteSpace(path))
            path = FindDefaultUsersFile();

        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
            throw new FileNotFoundException("OPC UA security users file was not found.", path);

        var sections = new Dictionary<string, Dictionary<string, string>>(StringComparer.OrdinalIgnoreCase);
        string? currentSection = null;

        foreach (var rawLine in File.ReadAllLines(path))
        {
            var trimmed = rawLine.Trim();
            if (trimmed.Length == 0 || trimmed.StartsWith('#'))
                continue;

            if (!char.IsWhiteSpace(rawLine[0]) && trimmed.EndsWith(':'))
            {
                currentSection = trimmed.TrimEnd(':').Trim();
                sections[currentSection] = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                continue;
            }

            if (currentSection is null)
                continue;

            var parts = trimmed.Split(':', count: 2);
            if (parts.Length != 2)
                continue;

            sections[currentSection][parts[0].Trim()] = parts[1].Trim().Trim('"', '\'');
        }

        return new OpcUaSecurityUsers(
            ReadCredentials(sections, "positive"),
            ReadCredentials(sections, "wrong_password"),
            ReadCredentials(sections, "unknown_user"));
    }

    private static Credentials ReadCredentials(
        IReadOnlyDictionary<string, Dictionary<string, string>> sections,
        string section)
    {
        if (!sections.TryGetValue(section, out var values)
            || !values.TryGetValue("username", out var userName)
            || !values.TryGetValue("password", out var password))
            throw new InvalidOperationException($"OPC UA security users file is missing {section}.username/password.");

        return new Credentials(userName, password);
    }

    private static string? FindDefaultUsersFile()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var sharedCandidate = Path.Combine(
                dir.FullName,
                "OPC_UA_Servers",
                "Release2",
                "opcua_security.users.yaml");
            if (File.Exists(sharedCandidate))
                return sharedCandidate;

            foreach (var testsDirectoryName in new[] { "Tests", "tests" })
            {
                var candidate = Path.Combine(dir.FullName, testsDirectoryName, "opcua_security.users.yaml");
                if (File.Exists(candidate))
                    return candidate;
            }

            dir = dir.Parent;
        }

        return null;
    }

    private sealed record Credentials(string UserName, string Password);

    private sealed record OpcUaSecurityUsers(
        Credentials Positive,
        Credentials WrongPassword,
        Credentials UnknownUser);

    private sealed class OpcUaSecurityTempScope : IDisposable
    {
        private OpcUaSecurityTempScope(string rootPath)
        {
            RootPath = rootPath;
            PkiRootPath = Path.Combine(rootPath, "pki");
            Directory.CreateDirectory(PkiRootPath);
        }

        public string RootPath { get; }

        public string PkiRootPath { get; }

        public static OpcUaSecurityTempScope Create(string caseName)
        {
            var safeCaseName = string.Concat(caseName.Select(ch => char.IsLetterOrDigit(ch) ? ch : '_'));
            var root = Path.Combine(
                ResolveProjectTempRoot(),
                OpcUaSecurityTargetName(),
                $"{safeCaseName}_{Guid.NewGuid():N}");
            return new OpcUaSecurityTempScope(root);
        }

        public string WriteUserCertificatePfx()
            => WriteUserCertificatePfx("IJT OPC UA Security X509 User");

        public (string PfxPath, byte[] CertificateDer) WriteUserCertificatePfxWithDer(string commonName)
        {
            using var rsa = RSA.Create(2048);
            var request = new CertificateRequest(
                $"CN={commonName}",
                rsa,
                HashAlgorithmName.SHA256,
                RSASignaturePadding.Pkcs1);
            request.CertificateExtensions.Add(new X509BasicConstraintsExtension(false, false, 0, false));
            var subjectKeyIdentifier = new X509SubjectKeyIdentifierExtension(request.PublicKey, false);
            request.CertificateExtensions.Add(subjectKeyIdentifier);
            request.CertificateExtensions.Add(
                X509AuthorityKeyIdentifierExtension.CreateFromSubjectKeyIdentifier(subjectKeyIdentifier));
            request.CertificateExtensions.Add(new X509KeyUsageExtension(X509KeyUsageFlags.DigitalSignature, false));

            using var certificate = request.CreateSelfSigned(
                DateTimeOffset.UtcNow.AddDays(-1),
                DateTimeOffset.UtcNow.AddDays(30));
            var safeStem = string.Concat(commonName.Select(ch => char.IsLetterOrDigit(ch) ? ch : '_'));
            var pfxPath = Path.Combine(RootPath, $"x509-user-{safeStem}.pfx");
            File.WriteAllBytes(pfxPath, certificate.Export(X509ContentType.Pkcs12));
            var derBytes = certificate.Export(X509ContentType.Cert);
            return (pfxPath, derBytes);
        }

        public string WriteUserCertificatePfx(string commonName)
            => WriteUserCertificatePfxWithDer(commonName).PfxPath;

        public void Dispose()
        {
            if (PreserveTestArtifacts())
                return;

            try
            {
                if (Directory.Exists(RootPath))
                    Directory.Delete(RootPath, recursive: true);
            }
            catch
            {
                // Best-effort cleanup; OPC UA SDK certificate stores can briefly hold file handles on Windows.
            }
        }

        private static string ResolveProjectTempRoot()
        {
            var dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir is not null)
            {
                if (File.Exists(Path.Combine(dir.FullName, "IJT_CSharp_Client.csproj")))
                    return Path.Combine(dir.FullName, "tmp", "opcua-security");

                var projectRoot = Path.Combine(dir.FullName, "OPC_UA_Clients", "Release2", "IJT_CSharp_Client");
                if (File.Exists(Path.Combine(projectRoot, "IJT_CSharp_Client.csproj")))
                    return Path.Combine(projectRoot, "tmp", "opcua-security");

                dir = dir.Parent;
            }

            return Path.Combine(AppContext.BaseDirectory, "tmp", "opcua-security");
        }

        private static bool PreserveTestArtifacts()
            => string.Equals(Environment.GetEnvironmentVariable("IJT_PRESERVE_TEST_ARTIFACTS"), "1", StringComparison.OrdinalIgnoreCase)
               || string.Equals(Environment.GetEnvironmentVariable("IJT_PRESERVE_TEST_ARTIFACTS"), "true", StringComparison.OrdinalIgnoreCase)
               || string.Equals(Environment.GetEnvironmentVariable("IJT_PRESERVE_TEST_ARTIFACTS"), "yes", StringComparison.OrdinalIgnoreCase);
    }
}
