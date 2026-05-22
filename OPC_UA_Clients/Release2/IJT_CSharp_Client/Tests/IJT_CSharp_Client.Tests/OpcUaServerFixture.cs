#nullable enable

using System.Diagnostics;
using System.Globalization;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Configuration;
using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;

namespace IJT_CSharp_Client.Tests;

/// <summary>
/// xUnit collection fixture that starts the OPC UA IJT Server Simulator before live integration
/// tests run and stops it afterwards.
///
/// Resolution order for the server executable:
///   1. IJT_OPCUA_SECURITY_SUT=windows uses the native copied-EXE path.
///   2. IJT_OPCUA_SECURITY_SUT=linux uses Docker Compose with the Linux server package.
///   3. When IJT_OPCUA_SECURITY_SUT is unset, the legacy native-then-Docker fallback remains.
///   4. Already-running OPC UA-ready server on the resolved port is reused only
///      when the runner did not request an explicit managed SUT.
///
/// Port resolution order (first match wins):
///   1. <c>OPCUA_SERVER_PORT</c> environment variable (integer)
///   2. Port parsed from <c>OPCUA_SERVER_URL</c> environment variable
///   3. Port parsed from <c>IJT_SERVER_URL</c> environment variable
///   4. Default: 40451
///
/// If the server cannot be started, <see cref="IsAvailable"/> is false and live tests
/// must skip themselves via <c>Skip.If(!Fixture.IsAvailable)</c>.
/// </summary>
public sealed class OpcUaServerFixture : IDisposable
{
    private const string DockerImageName = "opcua-ijt-server:latest";
    private const string LinuxSimulatorZipName = "OPC_UA_IJT_Server_Simulator_Linux.zip";
    // Compose --wait-timeout budgets. The 120s warm value covers the OPC UA
    // server compose healthcheck (nc -z, start_period 20s + interval 10s ×
    // retries 6 ≈ 80s) with margin. The 300s cold value adds image build.
    // These two are the only allowed compose --wait-timeout values for this
    // test fixture.
    private const int DockerComposeWarmWaitTimeoutSeconds = 120;
    private const int DockerComposeColdWaitTimeoutSeconds = 300;
    private const int DockerComposeCachedUpTimeoutMs = (DockerComposeWarmWaitTimeoutSeconds + 30) * 1000;
    private const int DockerComposeBuildUpTimeoutMs = (DockerComposeColdWaitTimeoutSeconds + 60) * 1000;
    private const int DockerComposeOutputTailLimit = 80;

    private static readonly ILogger _log = IjtLog.ForCategory("IJT.Tests.ServerFixture");
    private static readonly int _port = ResolvePort();
    private Process? _serverProcess;
    private bool _dockerStarted;
    private string? _dockerComposeDir;
    private string? _dockerComposeProjectName;
    private string? _tempServerDir;
    private string? _tempServerPkiDir;
    private readonly SemaphoreSlim _reusableSessionLock = new(1, 1);
    private JoiningSystem? _reusableSession;

    public bool IsAvailable { get; private set; }
    public string ServerUrl { get; } = $"opc.tcp://localhost:{_port}";
    public string? ClientPkiRootPath { get; private set; }
    public string? KnownX509UserCertificatePfxPath { get; private set; }

    public void TrustClientApplicationCertificates(string? clientPkiRootPath)
    {
        if (string.IsNullOrWhiteSpace(clientPkiRootPath) || _tempServerPkiDir is null)
            return;

        var sourceDir = Path.Combine(clientPkiRootPath, "own", "certs");
        if (!Directory.Exists(sourceDir))
            return;

        var targetDir = ApplicationTrustStorePath();
        if (targetDir is null)
            return;

        Directory.CreateDirectory(targetDir);
        foreach (var certificatePath in Directory.GetFiles(sourceDir, "*.der"))
        {
            // CodeQL note: 'Clear text storage of sensitive information' on this line
            // is a false positive. .der files are DER-encoded X.509 PUBLIC certificates
            // (no private key material). The source is produced by
            // JoiningSystem.EnsureApplicationCertificateForTestingAsync via the OPC UA
            // SDK's own/certs store, while private keys stay in own/private/*.pfx; see
            // the C# unit test that asserts the own/certs and own/private split.
            var targetPath = Path.Combine(targetDir, Path.GetFileName(certificatePath));
            File.Copy(certificatePath, targetPath, overwrite: true);
            _log.LogInformation(
                "Trusted client application certificate {Certificate} for local simulator.",
                targetPath);
        }
    }

    private string? ApplicationTrustStorePath()
    {
        if (_tempServerPkiDir is null)
            return null;

        // The simulator's server_configuration.json sets pkiDirectoryPath to
        // _tempServerPkiDir directly (no "pki" subdir), so the trust store
        // is rooted there for BOTH native Windows and Docker. Earlier code
        // added a "pki/" prefix on native Windows, which silently caused the
        // simulator to treat the seeded application certificate as unknown
        // and reject every secure handshake with BadSecurityChecksFailed.
        return ApplicationTrustStorePath(_tempServerPkiDir);
    }

    internal static string ApplicationTrustStorePath(string serverPkiRoot)
        => Path.Combine(serverPkiRoot, "DefaultApplicationGroup", "trusted", "certs");

    internal static string UserTokenTrustStorePath(string serverPkiRoot)
        => Path.Combine(serverPkiRoot, "DefaultUserTokenGroup", "trusted", "certs");

    /// <summary>
    /// Place a single X509 user-identity certificate (DER bytes) into the
    /// server's <c>DefaultUserTokenGroup/trusted/certs</c> store. Used by the
    /// X509 happy-path OPC UA security target before the live simulator starts.
    /// </summary>
    public void TrustUserTokenCertificate(byte[] certificateDer, string fileNameStem)
    {
        if (_tempServerPkiDir is null || certificateDer.Length == 0)
            return;

        var targetDir = UserTokenTrustStorePath(_tempServerPkiDir);
        Directory.CreateDirectory(targetDir);
        var safeStem = string.Concat(fileNameStem.Select(ch => char.IsLetterOrDigit(ch) ? ch : '_'));
        // CodeQL note: 'Clear text storage of sensitive information' on this line
        // is a false positive. certificateDer is DER-encoded X.509 PUBLIC user-identity
        // material from PrepareOpcUaSecurityKnownX509UserCertificate using
        // Export(X509ContentType.Cert), which excludes private key material. The
        // corresponding sensitive PFX is exported separately with X509ContentType.Pkcs12
        // and stored under KnownX509UserCertificatePfxPath.
        var targetPath = Path.Combine(targetDir, $"{safeStem}.der");
        File.WriteAllBytes(targetPath, certificateDer);
        _log.LogInformation(
            "Trusted X509 user-identity certificate {Certificate} in DefaultUserTokenGroup for local simulator.",
            targetPath);
    }

    public OpcUaServerFixture()
    {
        var testRunnerPort = Environment.GetEnvironmentVariable("OPCUA_SERVER_PORT");
        var managedByRunner = !string.IsNullOrWhiteSpace(testRunnerPort);
        var requestedSut = ResolveRequestedSut();
        var explicitManagedSut = requestedSut is not null && managedByRunner;

        // IJT_PHASE1_ONLY=true means we're in the unit-test phase of the root runner.
        // Auto-launching the server here would race with test execution; skip it and
        // let live tests mark themselves as skipped via Skip.If(!Fixture.IsAvailable).
        var phase1Only = string.Equals(
            Environment.GetEnvironmentVariable("IJT_PHASE1_ONLY"), "true",
            StringComparison.OrdinalIgnoreCase);
        if (phase1Only)
        {
            _log.LogInformation("IJT_PHASE1_ONLY=true — skipping server auto-launch. Live tests will be skipped.");
            IsAvailable = false;
            return;
        }

        byte[]? knownX509UserCertificateDer = null;
        if (IsOpcUaSecurityRun())
        {
            ClientPkiRootPath = PrepareOpcUaSecurityClientPkiRoot();
            (KnownX509UserCertificatePfxPath, knownX509UserCertificateDer) =
                PrepareOpcUaSecurityKnownX509UserCertificate();
        }

        if (IsPortOpen(_port))
        {
            if (explicitManagedSut)
            {
                _log.LogInformation(
                    "Explicit IJT_OPCUA_SECURITY_SUT={Sut} with OPCUA_SERVER_PORT set — killing stale process before isolated launch on port {Port}.",
                    requestedSut,
                    _port);
                KillProcessOnPort(_port);
                if (!WaitForPortClosed(_port, timeoutSeconds: 15))
                {
                    HandleExplicitSutUnavailable(
                        $"[OpcUaServerFixture] Port {_port} is still in use after stale-server cleanup.",
                        requestedSut);
                    return;
                }
            }
            else
            {
                var attempts = ProbeMaxAttempts();
                if (ProbeOpcUaReady(_port, maxAttempts: attempts, delayMs: 1000))
                {
                    _log.LogInformation(
                        "OPC UA server already ready on port {Port} — reusing existing server.",
                        _port);
                    IsAvailable = true;
                    return;
                }

                if (managedByRunner)
                {
                    _log.LogInformation(
                        "OPCUA_SERVER_PORT is set but port {Port} did not pass OPC UA readiness — killing stale process before fresh launch.",
                        _port);
                    KillProcessOnPort(_port);
                    if (!WaitForPortClosed(_port, timeoutSeconds: 15))
                    {
                        var msg = $"[OpcUaServerFixture] Port {_port} is still in use after stale-server cleanup. Live tests will be skipped.";
                        _log.LogWarning("{Message}", msg);
                        Console.Error.WriteLine(msg);
                        IsAvailable = false;
                        return;
                    }
                }
                else
                {
                    var msg = $"[OpcUaServerFixture] Port {_port} is open, but OPC UA did not become ready. Live tests will be skipped.";
                    _log.LogWarning("{Message}", msg);
                    Console.Error.WriteLine(msg);
                    IsAvailable = false;
                    return;
                }
            }
        }

        if (string.Equals(requestedSut, "linux", StringComparison.OrdinalIgnoreCase))
        {
            if (TryLaunchViaDocker(knownX509UserCertificateDer))
            {
                // ``docker compose up --wait`` already blocked on the OPC UA
                // server compose healthcheck (nc -z on the OPC UA port), so a
                // raw TCP probe here would be redundant. The protocol probe
                // alone is the readiness contract.
                IsAvailable = ProbeOpcUaReady(_port, maxAttempts: ProbeMaxAttempts(), delayMs: 1000);
                if (!IsAvailable)
                {
                    var msg = $"[OpcUaServerFixture] Docker OPC UA server did not become ready on port {_port}.";
                    HandleExplicitSutUnavailable(msg, requestedSut);
                }
                else
                    _log.LogInformation("OPC UA server (Docker) ready on port {Port}.", _port);
                return;
            }

            HandleExplicitSutUnavailable(
                $"[OpcUaServerFixture] IJT_OPCUA_SECURITY_SUT=linux requested, but Docker launch is unavailable on port {_port}.",
                requestedSut);
            return;
        }

        if (string.Equals(requestedSut, "windows", StringComparison.OrdinalIgnoreCase)
            && !RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            HandleExplicitSutUnavailable(
                $"[OpcUaServerFixture] IJT_OPCUA_SECURITY_SUT=windows requested on {RuntimeInformation.OSDescription}; run this OPC UA security target on Windows.",
                requestedSut);
            return;
        }

        var exePath = FindServerExecutable();
        if (exePath is null)
        {
            if (string.Equals(requestedSut, "windows", StringComparison.OrdinalIgnoreCase))
            {
                HandleExplicitSutUnavailable(
                    $"[OpcUaServerFixture] IJT_OPCUA_SECURITY_SUT=windows requested, but the Windows simulator executable was not found for port {_port}.",
                    requestedSut);
                return;
            }

            // No native binary — try Docker fallback
            if (TryLaunchViaDocker(knownX509UserCertificateDer))
            {
                // ``docker compose up --wait`` already proved port-open via the
                // compose healthcheck. Protocol probe is the single readiness
                // invariant; do not gate it behind a redundant TCP probe.
                IsAvailable = ProbeOpcUaReady(_port, maxAttempts: ProbeMaxAttempts(), delayMs: 1000);
                if (!IsAvailable)
                {
                    var msg = $"[OpcUaServerFixture] Docker OPC UA server did not become ready on port {_port}. Live tests will be skipped.";
                    _log.LogWarning("{Message}", msg);
                    Console.Error.WriteLine(msg);
                }
                else
                    _log.LogInformation("OPC UA server (Docker) ready on port {Port}.", _port);
                return;
            }
            var notFoundMsg = $"[OpcUaServerFixture] Server binary not found and Docker unavailable on port {_port}. Set OPCUA_SIMULATOR_EXE or ensure Docker is running. Live tests will be skipped.";
            _log.LogWarning("{Message}", notFoundMsg);
            Console.Error.WriteLine(notFoundMsg);
            IsAvailable = false;
            return;
        }

        _log.LogInformation("Starting OPC UA server: {Path}", exePath);
        try
        {
            // Managed security runs use an isolated copy so server JSON and PKI
            // changes never touch the checked-in package directory.
            if (_port != 40451 || IsOpcUaSecurityRun())
            {
                _log.LogInformation(
                    "Preparing isolated server copy for port {Port}. Source executable: {ExePath}",
                    _port, exePath);
                exePath = PrepareCopiedServerDir(exePath, _port, out _tempServerDir, out _tempServerPkiDir);
                _log.LogInformation(
                    "Isolated server copy prepared. Copied executable: {ExePath}, temp directory: {TempDir}, PKI directory: {PkiDir}",
                    exePath, _tempServerDir, _tempServerPkiDir);
                if (knownX509UserCertificateDer is not null && _tempServerDir is not null)
                    WriteOpcUaSecurityUserIdentityConfiguration(_tempServerDir, knownX509UserCertificateDer);
                TrustClientApplicationCertificates(ClientPkiRootPath);
                if (knownX509UserCertificateDer is not null)
                    TrustUserTokenCertificate(knownX509UserCertificateDer, "user1");
            }

            _serverProcess = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = exePath,
                    WorkingDirectory = Path.GetDirectoryName(exePath)!,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                },
                EnableRaisingEvents = true,
            };
            // No fixture-level simulator environment override here. Windows
            // path-length safety is handled by ResolveShortFixtureRoot() below
            // so this fixture does not depend on an undocumented simulator
            // switch.
            _serverProcess.OutputDataReceived += (_, e) =>
            {
                if (!string.IsNullOrWhiteSpace(e.Data))
                    LogServerOutput(e.Data);
            };
            _serverProcess.ErrorDataReceived += (_, e) =>
            {
                if (!string.IsNullOrWhiteSpace(e.Data))
                    _log.LogWarning("server stderr: {Line}", e.Data);
            };
            _serverProcess.Start();
            _serverProcess.BeginOutputReadLine();
            _serverProcess.BeginErrorReadLine();

            // Step 3: OPC UA readiness probe — verify the process is alive and the OPC UA
            // service layer is accepting connections (not just TCP).  The server opens the
            // TCP listener before the OPC UA stack is fully initialised, so we retry with
            // back-off rather than using a fixed sleep. ProbeOpcUaReady includes its own
            // attempts × delay budget, so a separate TCP-port wait would be redundant.
            var attempts = ProbeMaxAttempts();
            IsAvailable = ProbeOpcUaReady(_port, maxAttempts: attempts, delayMs: 1000);
            if (!IsAvailable)
            {
                var probeMsg = $"[OpcUaServerFixture] Server on port {_port} did not accept OPC UA connections within timeout. Live tests will be skipped.";
                _log.LogWarning("{Message}", probeMsg);
                Console.Error.WriteLine(probeMsg);
            }
            else
                _log.LogInformation("OPC UA server ready on port {Port}.", _port);
        }
        catch (Exception ex)
        {
            var catchMsg = $"[OpcUaServerFixture] Failed to start server on port {_port}. Live tests will be skipped. {ex}";
            _log.LogWarning("{Message}", catchMsg);
            Console.Error.WriteLine(catchMsg);
            IsAvailable = false;
        }
    }

    public async Task<JoiningSystem> OpenReusableSessionAsync(
        ClientConfig config,
        CancellationToken ct = default)
    {
        if (!IsAvailable)
            throw new InvalidOperationException("OPC UA server not available.");

        await _reusableSessionLock.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            if (_reusableSession is null || !_reusableSession.IsConnected)
            {
                if (_reusableSession is not null)
                {
                    await _reusableSession.DisposeAsync().ConfigureAwait(false);
                    _reusableSession = null;
                }

                _reusableSession = await JoiningSystem.ConnectAsync(config, ct).ConfigureAwait(false);
            }

            return _reusableSession;
        }
        finally
        {
            _reusableSessionLock.Release();
        }
    }

    public async Task CloseReusableSessionAsync(CancellationToken ct = default)
    {
        await _reusableSessionLock.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            if (_reusableSession is not null)
            {
                await _reusableSession.DisposeAsync().ConfigureAwait(false);
                _reusableSession = null;
            }
        }
        finally
        {
            _reusableSessionLock.Release();
        }
    }

    /// <summary>
    /// Resolves the OPC UA server port from environment variables with a fallback to 40451.
    /// </summary>
    private static int ResolvePort()
    {
        // 1 — explicit port number
        var portStr = Environment.GetEnvironmentVariable("OPCUA_SERVER_PORT");
        if (!string.IsNullOrWhiteSpace(portStr) && int.TryParse(portStr, out var explicitPort) && explicitPort > 0)
            return explicitPort;

        // 2/3 — parse from server URL env vars
        foreach (var key in new[] { "OPCUA_SERVER_URL", "IJT_SERVER_URL" })
        {
            var url = Environment.GetEnvironmentVariable(key);
            if (!string.IsNullOrWhiteSpace(url)
                && Uri.TryCreate(url, UriKind.Absolute, out var uri)
                && uri.Port > 0)
                return uri.Port;
        }

        return 40451;
    }

    private static int ProbeMaxAttempts()
    {
        var isCi = string.Equals(Environment.GetEnvironmentVariable("CI"), "true", StringComparison.OrdinalIgnoreCase)
            || string.Equals(Environment.GetEnvironmentVariable("GITHUB_ACTIONS"), "true", StringComparison.OrdinalIgnoreCase);
        return isCi ? 30 : 20;
    }

    private static string? ResolveRequestedSut()
    {
        var sut = Environment.GetEnvironmentVariable("IJT_OPCUA_SECURITY_SUT");
        if (string.IsNullOrWhiteSpace(sut))
            return null;

        if (string.Equals(sut, "windows", StringComparison.OrdinalIgnoreCase))
            return "windows";
        if (string.Equals(sut, "linux", StringComparison.OrdinalIgnoreCase))
            return "linux";

        throw new InvalidOperationException($"Unsupported IJT_OPCUA_SECURITY_SUT value: {sut}. Expected windows or linux.");
    }

    private static bool IsCiLike()
        => string.Equals(Environment.GetEnvironmentVariable("CI"), "true", StringComparison.OrdinalIgnoreCase)
           || string.Equals(Environment.GetEnvironmentVariable("GITHUB_ACTIONS"), "true", StringComparison.OrdinalIgnoreCase);

    private void HandleExplicitSutUnavailable(string message, string? requestedSut)
    {
        _log.LogWarning("{Message}", message);
        Console.Error.WriteLine(message);
        IsAvailable = false;
        if (requestedSut is not null && IsCiLike())
            throw new InvalidOperationException(message);
    }

    private static string? FindServerExecutable()
    {
        // 1 — env var
        var fromEnv = Environment.GetEnvironmentVariable("OPCUA_SIMULATOR_EXE");
        if (!string.IsNullOrWhiteSpace(fromEnv) && File.Exists(fromEnv))
            return fromEnv;

        // 2 — walk up from assembly location to find repo root (contains OPC_UA_Servers/)
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (Directory.Exists(Path.Combine(dir.FullName, "OPC_UA_Servers")))
                break;
            dir = dir.Parent;
        }

        if (dir is null) return null;

        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            var win = Path.Combine(dir.FullName, "OPC_UA_Servers", "Release2",
                "OPC_UA_IJT_Server_Simulator", "opcua_ijt_demo_application.exe");
            if (File.Exists(win)) return win;
        }
        else
        {
            var lin = Path.Combine(dir.FullName, "OPC_UA_Servers", "Release2",
                "OPC_UA_IJT_Server_Simulator_Linux", "opcua_ijt_demo_application");
            if (File.Exists(lin)) return lin;
        }

        return null;
    }

    /// <summary>Try to start the OPC UA server via Docker Compose.</summary>
    private bool TryLaunchViaDocker(byte[]? knownX509UserCertificateDer)
    {
        var dockerExe = FindDockerExecutable();
        if (dockerExe is null)
        {
            _log.LogInformation("Docker not found in PATH — skipping Docker fallback.");
            return false;
        }

        // Walk up from assembly location to find repo root
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (Directory.Exists(Path.Combine(dir.FullName, "OPC_UA_Servers")))
                break;
            dir = dir.Parent;
        }
        if (dir is null)
        {
            _log.LogInformation("Repo root not found from {Base} — Docker fallback unavailable.", AppContext.BaseDirectory);
            return false;
        }

        var composeDir = Path.Combine(dir.FullName, "OPC_UA_Servers", "Release2");
        if (!File.Exists(Path.Combine(composeDir, "docker-compose.yml")))
        {
            _log.LogInformation("docker-compose.yml not found in {Dir} — Docker fallback unavailable.", composeDir);
            return false;
        }

        _dockerComposeProjectName = ResolveDockerComposeProjectName();
        _log.LogInformation(
            "Starting OPC UA server via Docker in {Dir} with compose project {ProjectName}",
            composeDir,
            _dockerComposeProjectName);
        try
        {
            var composeFile = Path.Combine(composeDir, "docker-compose.yml");
            var startInfo = new ProcessStartInfo
            {
                FileName = dockerExe,
                WorkingDirectory = composeDir,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
            };
            startInfo.ArgumentList.Add("compose");

            if (knownX509UserCertificateDer is not null)
            {
                var overrideFile = PrepareDockerOpcUaSecurityOverride(
                    knownX509UserCertificateDer,
                    out _tempServerDir,
                    out _tempServerPkiDir);
                startInfo.ArgumentList.Add("-f");
                startInfo.ArgumentList.Add(composeFile);
                startInfo.ArgumentList.Add("-f");
                startInfo.ArgumentList.Add(overrideFile);
            }

            startInfo.ArgumentList.Add("up");
            startInfo.ArgumentList.Add("-d");
            var wantsBuild = ShouldBuildDockerImage(dockerExe, composeDir);
            if (wantsBuild)
                startInfo.ArgumentList.Add("--build");
            // compose --wait makes Docker itself the synchronization primitive:
            // the invocation blocks until the OPC UA server compose
            // healthcheck (nc -z on the OPC UA port) reports healthy. Without
            // this, "up -d" returned as soon as the container started and the
            // caller had to poll, producing flaky readiness behaviour.
            startInfo.ArgumentList.Add("--wait");
            startInfo.ArgumentList.Add("--wait-timeout");
            startInfo.ArgumentList.Add(
                (wantsBuild
                    ? DockerComposeColdWaitTimeoutSeconds
                    : DockerComposeWarmWaitTimeoutSeconds).ToString(CultureInfo.InvariantCulture));
            var timeoutMs = DockerComposeUpTimeoutMs(wantsBuild);

            using var r = new Process
            {
                StartInfo = startInfo,
            };
            // Enforce the resolved port so docker-compose uses the same port the test
            // fixture is about to connect to (avoids mismatch when _port was parsed from
            // OPCUA_SERVER_URL rather than being set via OPCUA_SERVER_PORT directly).
            r.StartInfo.Environment["OPCUA_SERVER_PORT"] = _port.ToString();
            r.StartInfo.Environment["COMPOSE_PROJECT_NAME"] = _dockerComposeProjectName;
            var outputLines = new List<string>();
            var outputLock = new object();
            r.OutputDataReceived += (_, e) => AppendDockerComposeOutput(outputLines, outputLock, "stdout", e.Data);
            r.ErrorDataReceived += (_, e) => AppendDockerComposeOutput(outputLines, outputLock, "stderr", e.Data);
            r.Start();
            r.BeginOutputReadLine();
            r.BeginErrorReadLine();
            if (!r.WaitForExit(timeoutMs))
            {
                _log.LogWarning(
                    "docker compose up timed out after {TimeoutMs}ms (build={Build}); killing process tree. Recent output:{Output}",
                    timeoutMs,
                    wantsBuild,
                    DockerComposeOutputTail(outputLines, outputLock));
                KillProcessTree(r);
                return false;
            }
            r.WaitForExit();
            if (r.ExitCode == 0)
            {
                _dockerStarted = true;
                _dockerComposeDir = composeDir;
                _log.LogInformation("Docker compose up succeeded (build={Build}).", wantsBuild);
                return true;
            }
            _log.LogWarning(
                "docker compose up exited with code {Code} (build={Build}). Recent output:{Output}",
                r.ExitCode,
                wantsBuild,
                DockerComposeOutputTail(outputLines, outputLock));
            return false;
        }
        catch (Exception ex)
        {
            _log.LogWarning("Docker launch failed: {Message}", ex.Message);
            return false;
        }
    }

    private string PrepareDockerOpcUaSecurityOverride(
        byte[] knownX509UserCertificateDer,
        out string tmpDir,
        out string pkiDir)
    {
        tmpDir = Path.Combine(
            ResolveProjectTempRoot("docker-overrides"),
            $"csharp_{_port}_{Guid.NewGuid():N}");
        pkiDir = ResolveShortServerPkiDirectory(_port);
        Directory.CreateDirectory(tmpDir);

        WriteOpcUaSecurityUserIdentityConfiguration(tmpDir, knownX509UserCertificateDer);
        TrustDockerClientApplicationCertificates(pkiDir, ClientPkiRootPath);
        TrustDockerCertificate(pkiDir, "DefaultUserTokenGroup", knownX509UserCertificateDer, "user1");
        AllowContainerWrite(pkiDir);

        var configPath = Path.Combine(tmpDir, "user_identity_configuration.json");
        var overridePath = Path.Combine(tmpDir, "docker-compose.opcua-security.yml");
        File.WriteAllText(
            overridePath,
            string.Join(
                Environment.NewLine,
                [
                    "services:",
                    "  opcua-ijt-server:",
                    "    volumes:",
                    $"      - \"{ToDockerBindPath(configPath)}:/app/user_identity_configuration.json:ro\"",
                    $"      - \"{ToDockerBindPath(pkiDir)}:/app/pki\"",
                    "",
                ]),
            System.Text.Encoding.UTF8);
        return overridePath;
    }

    private static void TrustDockerClientApplicationCertificates(string pkiDir, string? clientPkiRootPath)
    {
        if (string.IsNullOrWhiteSpace(clientPkiRootPath))
            return;

        var sourceDir = Path.Combine(clientPkiRootPath, "own", "certs");
        if (!Directory.Exists(sourceDir))
            return;

        foreach (var certificatePath in Directory.GetFiles(sourceDir, "*.der"))
            TrustDockerCertificate(
                pkiDir,
                "DefaultApplicationGroup",
                File.ReadAllBytes(certificatePath),
                Path.GetFileNameWithoutExtension(certificatePath));
    }

    private static void TrustDockerCertificate(
        string pkiDir,
        string groupName,
        byte[] certificateDer,
        string fileNameStem)
    {
        var targetDir = Path.Combine(pkiDir, groupName, "trusted", "certs");
        Directory.CreateDirectory(targetDir);
        var safeStem = string.Concat(fileNameStem.Select(ch => char.IsLetterOrDigit(ch) ? ch : '_'));
        File.WriteAllBytes(Path.Combine(targetDir, $"{safeStem}.der"), certificateDer);
    }

    private static void AllowContainerWrite(string path)
    {
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            return;

        try
        {
            using var chmod = Process.Start(new ProcessStartInfo
            {
                FileName = "chmod",
                ArgumentList = { "-R", "777", path },
                UseShellExecute = false,
                CreateNoWindow = true,
            });
            chmod?.WaitForExit(3000);
        }
        catch (Exception ex)
        {
            _log.LogWarning("Could not relax Docker PKI directory permissions: {Message}", ex.Message);
        }
    }

    private static string ToDockerBindPath(string path)
        => Path.GetFullPath(path).Replace('\\', '/');

    private static bool ShouldBuildDockerImage(string dockerExe, string composeDir)
    {
        var value = Environment.GetEnvironmentVariable("IJT_DOCKER_COMPOSE_BUILD");
        if (string.Equals(value, "1", StringComparison.OrdinalIgnoreCase)
            || string.Equals(value, "true", StringComparison.OrdinalIgnoreCase)
            || string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase)
            || string.Equals(value, "on", StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }

        return DockerImageIsMissingOrOlderThanSimulatorZip(dockerExe, composeDir);
    }

    private static int DockerComposeUpTimeoutMs(bool wantsBuild)
        => wantsBuild ? DockerComposeBuildUpTimeoutMs : DockerComposeCachedUpTimeoutMs;

    private static void AppendDockerComposeOutput(
        List<string> lines,
        object syncRoot,
        string stream,
        string? line)
    {
        if (line is null)
            return;

        lock (syncRoot)
        {
            lines.Add($"{stream}: {line}");
            if (lines.Count > DockerComposeOutputTailLimit)
                lines.RemoveRange(0, lines.Count - DockerComposeOutputTailLimit);
        }
    }

    private static string DockerComposeOutputTail(List<string> lines, object syncRoot)
    {
        lock (syncRoot)
        {
            return lines.Count == 0
                ? " <no output captured>"
                : Environment.NewLine + string.Join(Environment.NewLine, lines);
        }
    }

    private static void KillProcessTree(Process process)
    {
        try
        {
            if (!process.HasExited)
                process.Kill(entireProcessTree: true);
        }
        catch (Exception ex)
        {
            _log.LogWarning("Could not kill timed-out docker compose process: {Message}", ex.Message);
        }

        try
        {
            process.WaitForExit(10_000);
        }
        catch (Exception ex)
        {
            _log.LogWarning("Could not wait for timed-out docker compose process to exit: {Message}", ex.Message);
        }
    }

    private static bool DockerImageIsMissingOrOlderThanSimulatorZip(string dockerExe, string composeDir)
    {
        var zipPath = Path.Combine(composeDir, LinuxSimulatorZipName);
        if (!File.Exists(zipPath))
            return false;

        var imageCreatedUtc = DockerImageCreatedUtc(dockerExe, composeDir);
        if (imageCreatedUtc is null)
            return true;

        return File.GetLastWriteTimeUtc(zipPath) > imageCreatedUtc.Value.UtcDateTime;
    }

    private static DateTimeOffset? DockerImageCreatedUtc(string dockerExe, string composeDir)
    {
        try
        {
            using var inspect = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = dockerExe,
                    WorkingDirectory = composeDir,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                },
            };
            inspect.StartInfo.ArgumentList.Add("image");
            inspect.StartInfo.ArgumentList.Add("inspect");
            inspect.StartInfo.ArgumentList.Add(DockerImageName);
            inspect.StartInfo.ArgumentList.Add("--format");
            inspect.StartInfo.ArgumentList.Add("{{.Created}}");

            inspect.Start();
            if (!inspect.WaitForExit(10_000))
            {
                inspect.Kill(entireProcessTree: true);
                return null;
            }

            var created = inspect.StandardOutput.ReadToEnd().Trim();
            _ = inspect.StandardError.ReadToEnd();
            if (inspect.ExitCode != 0)
                return null;

            return DateTimeOffset.TryParse(
                created,
                CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                out var parsed)
                ? parsed
                : null;
        }
        catch (Exception ex)
        {
            _log.LogDebug("Could not inspect Docker image {Image}: {Message}", DockerImageName, ex.Message);
            return null;
        }
    }

    private static string? FindInPath(string exe)
    {
        var pathEnv = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
        foreach (var segment in pathEnv.Split(Path.PathSeparator))
        {
            var full = Path.Join(segment, exe);
            if (File.Exists(full)) return full;
        }
        return null;
    }

    private static string? FindDockerExecutable()
        => RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
            ? FindInPath("docker.exe")
            : FindInPath("docker");

    private static string ResolveDockerComposeProjectName()
    {
        var fromEnv = Environment.GetEnvironmentVariable("COMPOSE_PROJECT_NAME");
        if (!string.IsNullOrWhiteSpace(fromEnv))
            return fromEnv;

        var target = Environment.GetEnvironmentVariable("IJT_OPCUA_SECURITY_TARGET");
        var suffix = string.IsNullOrWhiteSpace(target) ? _port.ToString() : target.ToLowerInvariant();
        return $"ijt_csharp_opcua_security_{suffix}";
    }

    private static bool IsOpcUaSecurityRun()
        => !string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("IJT_OPCUA_SECURITY_TARGET"))
           || string.Equals(Environment.GetEnvironmentVariable("IJT_OPCUA_SECURITY_SUT"), "windows", StringComparison.OrdinalIgnoreCase)
           || string.Equals(Environment.GetEnvironmentVariable("IJT_OPCUA_SECURITY_SUT"), "linux", StringComparison.OrdinalIgnoreCase);

    private static string PrepareOpcUaSecurityClientPkiRoot()
    {
        var suffix = Guid.NewGuid().ToString("N")[..8];
        var pkiRoot = Path.Combine(ResolveProjectTempRoot("client-pki"), $"{OpcUaSecurityIdentity.TargetName()}_{suffix}");
        Directory.CreateDirectory(pkiRoot);

        var config = new ClientConfig
        {
            ServerUrl = $"opc.tcp://localhost:{_port}",
            ApplicationName = OpcUaSecurityIdentity.CSharpClientApplicationName(),
            AutoAcceptServerCertificate = true,
            UseSecurityPolicyForEndpointDiscovery = true,
            SecurityPolicyUri = Opc.Ua.SecurityPolicies.Basic256Sha256,
            MessageSecurityMode = Opc.Ua.MessageSecurityMode.SignAndEncrypt,
            PkiRootPath = pkiRoot,
        };
        JoiningSystem.EnsureApplicationCertificateForTestingAsync(config).GetAwaiter().GetResult();
        return pkiRoot;
    }

    private static (string PfxPath, byte[] CertificateDer) PrepareOpcUaSecurityKnownX509UserCertificate()
    {
        var target = Environment.GetEnvironmentVariable("IJT_OPCUA_SECURITY_TARGET");
        target = string.IsNullOrWhiteSpace(target) ? "local" : target.ToLowerInvariant();
        var root = Path.Combine(ResolveProjectTempRoot("client-pki"), $"{target}_x509_user1_{Guid.NewGuid():N}");
        Directory.CreateDirectory(root);

        using var rsa = RSA.Create(2048);
        var request = new CertificateRequest(
            "CN=user1",
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

        var pfxPath = Path.Combine(root, "x509-user1.pfx");
        File.WriteAllBytes(pfxPath, certificate.Export(X509ContentType.Pkcs12));
        return (pfxPath, certificate.Export(X509ContentType.Cert));
    }

    private static void WriteOpcUaSecurityUserIdentityConfiguration(
        string serverDir,
        byte[] knownX509UserCertificateDer)
    {
        var users = LoadOpcUaSecurityUsersForFixture();
        var configuredUsers = new Dictionary<string, Dictionary<string, object>>(StringComparer.Ordinal);

        configuredUsers[users.Positive.UserName] = User(
            users.Positive.UserName,
            users.Positive.Password,
            users.Positive.UserName == "SecurityAdmin" ? ["SecurityAdmin"] : [],
            "OPC UA security positive user");

        configuredUsers.TryAdd(
            users.WrongPassword.UserName,
            User(users.WrongPassword.UserName, "password", [], "OPC UA security wrong-password target"));

        // user1 needs the SecurityAdmin role so the activated session has Browse/Read
        // permission on standard ns=0 Server nodes (required by the .NET SDK to read
        // i=2255 NamespaceArray during session activation, and by AssertBenignFlowAsync
        // afterwards). The X509 thumbprint authentication path is still exercised end
        // to end; only the post-authentication permission set is widened.
        configuredUsers.TryAdd("user1", User("user1", "password", [], "OPC UA security X509 user"));
        EnsureUserHasRole(configuredUsers["user1"], "SecurityAdmin");
        configuredUsers["user1"]["x509ThumbprintSha1Hex"] = Convert.ToHexString(
            SHA1.HashData(knownX509UserCertificateDer)).ToLowerInvariant();

        var payload = new
        {
            userIdentityData = new
            {
                enabled = true,
                users = configuredUsers.Values,
            },
        };
        var json = JsonSerializer.Serialize(
            payload,
            new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(
            Path.Combine(serverDir, "user_identity_configuration.json"),
            json + Environment.NewLine,
            System.Text.Encoding.UTF8);
    }

    private static void EnsureUserHasRole(Dictionary<string, object> user, string role)
    {
        var roles = user.TryGetValue("roles", out var value) && value is string[] existing
            ? existing
            : [];
        if (Array.Exists(roles, current => string.Equals(current, role, StringComparison.Ordinal)))
            return;

        var merged = new string[roles.Length + 1];
        Array.Copy(roles, merged, roles.Length);
        merged[^1] = role;
        user["roles"] = merged;
    }

    private static Dictionary<string, object> User(
        string userName,
        string password,
        string[] roles,
        string description)
        => new(StringComparer.Ordinal)
        {
            ["userName"] = userName,
            ["password"] = password,
            ["roles"] = roles,
            ["description"] = description,
        };

    private static FixtureOpcUaSecurityUsers LoadOpcUaSecurityUsersForFixture()
    {
        var path = Environment.GetEnvironmentVariable("OPCUA_SECURITY_USERS_FILE");
        if (string.IsNullOrWhiteSpace(path))
            path = FindDefaultUsersFileForFixture();

        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
            return new FixtureOpcUaSecurityUsers(
                new FixtureCredentials("SecurityAdmin", "password"),
                new FixtureCredentials("user1", "wrong_xxxxx"));

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
            if (parts.Length == 2)
                sections[currentSection][parts[0].Trim()] = parts[1].Trim().Trim('"', '\'');
        }

        return new FixtureOpcUaSecurityUsers(
            ReadFixtureCredentials(sections, "positive", new FixtureCredentials("SecurityAdmin", "password")),
            ReadFixtureCredentials(sections, "wrong_password", new FixtureCredentials("user1", "wrong_xxxxx")));
    }

    private static FixtureCredentials ReadFixtureCredentials(
        IReadOnlyDictionary<string, Dictionary<string, string>> sections,
        string section,
        FixtureCredentials fallback)
    {
        if (!sections.TryGetValue(section, out var values)
            || !values.TryGetValue("username", out var userName)
            || !values.TryGetValue("password", out var password))
        {
            return fallback;
        }

        return new FixtureCredentials(userName, password);
    }

    private static string? FindDefaultUsersFileForFixture()
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

    private sealed record FixtureCredentials(string UserName, string Password);

    private sealed record FixtureOpcUaSecurityUsers(
        FixtureCredentials Positive,
        FixtureCredentials WrongPassword);

    private static bool IsPortOpen(int port)
    {
        try
        {
            using var tcp = new TcpClient();
            tcp.Connect("127.0.0.1", port);
            return true;
        }
        catch (Exception) { return false; }
    }

    /// <summary>
    /// Clears an isolated test port before a managed launch. Docker containers
    /// publishing the port are stopped first; native listeners use platform-specific
    /// commands (netstat + taskkill on Windows, fuser on Linux/macOS).
    /// </summary>
    private static void KillProcessOnPort(int port)
    {
        try
        {
            if (StopDockerContainersPublishingPort(port))
            {
                return;
            }

            if (string.Equals(
                    Environment.GetEnvironmentVariable("IJT_OPCUA_SECURITY_SUT"),
                    "linux",
                    StringComparison.OrdinalIgnoreCase))
            {
                return;
            }

            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                // netstat -ano lists PID in the last column for LISTENING entries
                using var ns = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = "netstat.exe",
                        Arguments = "-ano",
                        UseShellExecute = false,
                        RedirectStandardOutput = true,
                        CreateNoWindow = true,
                    },
                };
                ns.Start();
                var output = ns.StandardOutput.ReadToEnd();
                ns.WaitForExit(5000);

                foreach (var line in output.Split('\n'))
                {
                    if (!line.Contains($":{port} ") && !line.Contains($":{port}\t")) continue;
                    if (!line.Contains("LISTENING")) continue;
                    var parts = line.Trim().Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                    if (parts.Length >= 5 && int.TryParse(parts[^1], out var pid) && pid > 0)
                    {
                        _log.LogInformation("Killing stale server process PID {Pid} on port {Port}.", pid, port);
                        using var kill = Process.Start(new ProcessStartInfo
                        {
                            FileName = "taskkill.exe",
                            Arguments = $"/F /T /PID {pid}",
                            UseShellExecute = false,
                            CreateNoWindow = true,
                        });
                        kill?.WaitForExit(3000);
                    }
                }
            }
            else
            {
                // fuser -k <port>/tcp on Linux/macOS
                using var fuser = Process.Start(new ProcessStartInfo
                {
                    FileName = "fuser",
                    Arguments = $"-k {port}/tcp",
                    UseShellExecute = false,
                    CreateNoWindow = true,
                });
                fuser?.WaitForExit(5000);
            }
        }
        catch (Exception ex)
        {
            _log.LogWarning("KillProcessOnPort({Port}) failed (non-fatal): {Message}", port, ex.Message);
        }
    }

    private static bool StopDockerContainersPublishingPort(int port)
    {
        var dockerExe = FindDockerExecutable();
        if (dockerExe is null)
            return false;

        try
        {
            using var ps = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = dockerExe,
                    Arguments = $"ps --filter publish={port} --format \"{{{{.ID}}}}\"",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                },
            };
            ps.Start();
            if (!ps.WaitForExit(5000))
            {
                ps.Kill(entireProcessTree: true);
                return false;
            }
            var output = ps.StandardOutput.ReadToEnd();
            if (ps.ExitCode != 0)
            {
                return false;
            }

            var stoppedAny = false;
            foreach (var containerId in output.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
            {
                using var stop = Process.Start(new ProcessStartInfo
                {
                    FileName = dockerExe,
                    Arguments = $"stop {containerId}",
                    UseShellExecute = false,
                    CreateNoWindow = true,
                });
                stop?.WaitForExit(10000);
                stoppedAny = true;
            }

            return stoppedAny;
        }
        catch (Exception ex)
        {
            _log.LogDebug("Docker port cleanup for port {Port} was skipped: {Message}", port, ex.Message);
            return false;
        }
    }


    // NOTE: Do not reintroduce a TCP-only ``WaitForPort`` readiness gate.
    // After ``docker compose up --wait`` the compose healthcheck already
    // proves the OPC UA TCP port is open; for the native-EXE path, the
    // ProbeOpcUaReady retry loop spans the same window and is a strictly
    // stronger guarantee. The live readiness contract forbids re-introducing
    // a Thread.Sleep-based port wait alongside the protocol probe.

    private static bool WaitForPortClosed(int port, int timeoutSeconds)
    {
        var deadline = DateTime.UtcNow.AddSeconds(timeoutSeconds);
        while (DateTime.UtcNow < deadline)
        {
            if (!IsPortOpen(port)) return true;
            Thread.Sleep(500);
        }
        return !IsPortOpen(port);
    }

    /// <summary>
    /// Probes the OPC UA server by sending a binary Hello message and checking for an
    /// Acknowledge response.  This confirms the OPC UA stack is initialised, not just
    /// that the TCP port is open.  Retries with a fixed delay to allow the server time
    /// to fully start.  Returns <c>true</c> when the probe succeeds.
    /// </summary>
    private static bool ProbeOpcUaReady(int port, int maxAttempts, int delayMs)
    {
        // OPC UA Binary Hello message (UABH) — minimal well-formed hello for opc.tcp
        // Layout: MessageType(3) + 'F'(1) + MessageSize(4-LE) + Version(4-LE) +
        //         ReceiveBufSize(4-LE) + SendBufSize(4-LE) + MaxMsgSize(4-LE) +
        //         MaxChunkCount(4-LE) + EndpointUrl length(4-LE) + EndpointUrl bytes
        var url = $"opc.tcp://localhost:{port}";
        var urlBytes = System.Text.Encoding.UTF8.GetBytes(url);
        // Message layout: 28 bytes fixed fields + 4 bytes URL length + N URL bytes
        var msgSize = 32 + urlBytes.Length;
        var hello = new byte[msgSize];
        // Message type "HEL" + chunk type 'F'
        hello[0] = (byte)'H'; hello[1] = (byte)'E'; hello[2] = (byte)'L'; hello[3] = (byte)'F';
        // Message size (little-endian)
        BitConverter.GetBytes(msgSize).CopyTo(hello, 4);
        // Protocol version = 0
        BitConverter.GetBytes(0u).CopyTo(hello, 8);
        // Receive buffer size = 65535
        BitConverter.GetBytes(65535u).CopyTo(hello, 12);
        // Send buffer size = 65535
        BitConverter.GetBytes(65535u).CopyTo(hello, 16);
        // Max message size = 0 (unlimited)
        BitConverter.GetBytes(0u).CopyTo(hello, 20);
        // Max chunk count = 0 (unlimited)
        BitConverter.GetBytes(0u).CopyTo(hello, 24);
        // Endpoint URL length + bytes
        BitConverter.GetBytes(urlBytes.Length).CopyTo(hello, 28);
        urlBytes.CopyTo(hello, 32);

        for (var attempt = 1; attempt <= maxAttempts; attempt++)
        {
            try
            {
                using var tcp = new TcpClient();
                tcp.Connect("127.0.0.1", port);
                tcp.ReceiveTimeout = 3000;
                tcp.SendTimeout = 3000;
                var stream = tcp.GetStream();
                stream.Write(hello, 0, hello.Length);
                // Read at least 4 bytes — enough to check the response message type
                var buf = new byte[8];
                var read = stream.Read(buf, 0, buf.Length);
                // OPC UA Acknowledge is "ACK" + 'F'; OPC UA Error is "ERR" + 'F'
                // Either response means the OPC UA stack is alive and responding
                if (read >= 4
                    && buf[3] == (byte)'F'
                    && ((buf[0] == 'A' && buf[1] == 'C' && buf[2] == 'K')
                        || (buf[0] == 'E' && buf[1] == 'R' && buf[2] == 'R')))
                {
                    _log.LogInformation("OPC UA probe succeeded on port {Port} (attempt {Attempt}/{Max}).", port, attempt, maxAttempts);
                    return true;
                }
            }
            catch (Exception)
            {
                // Not ready yet — will retry
            }

            if (attempt < maxAttempts)
                Thread.Sleep(delayMs);
        }

        _log.LogWarning("OPC UA probe failed after {Max} attempts on port {Port}.", maxAttempts, port);
        return false;
    }


    /// <summary>
    /// Copies the server binary directory to a temp location and patches
    /// <c>server_configuration.json</c> so the server starts on <paramref name="port"/>.
    /// Returns the path to the copied executable.
    /// </summary>
    /// <remarks>
    /// The server EXE reads its configuration from <c>server_configuration.json</c>
    /// in its working directory, which overrides any environment variable. To run
    /// on a non-default port without modifying the source files, we copy the entire
    /// binary directory to a temp location and patch the JSON in the copy. This is
    /// the same copy-patch pattern used by the Python clients via <c>run_all_tests.py</c>.
    /// </remarks>
    private static string PrepareCopiedServerDir(string srcExePath, int port, out string tmpDir, out string pkiDir)
    {
        var srcDir = Path.GetDirectoryName(srcExePath)!;
        // Use the short-root helper for the EXE copy as well. Avoids spurious
        // "Path Length exceeds Safe Threshold" warnings from the simulator
        // when the GitHub Actions workspace prefix plus the project-nested
        // bin path push the binary install path past 145 chars on Windows.
        var tmpRoot = ResolveShortFixtureRoot("server-copies");
        Directory.CreateDirectory(tmpRoot);
        tmpDir = Path.Combine(tmpRoot, $"opcua_csharp_{port}_{Guid.NewGuid():N}");
        pkiDir = ResolveShortServerPkiDirectory(port);

        CopyDirectoryRecursive(srcDir, tmpDir);

        var cfgPath = Path.Combine(tmpDir, "server_configuration.json");
        if (File.Exists(cfgPath))
        {
            var json = File.ReadAllText(cfgPath);
            var patched = System.Text.RegularExpressions.Regex.Replace(
                json,
                @"""serverEndpointTCPPort""\s*:\s*\d+",
                $@"""serverEndpointTCPPort"": {port}");
            patched = System.Text.RegularExpressions.Regex.Replace(
                patched,
                @"""pkiDirectoryPath""\s*:\s*""[^""]*""",
                $@"""pkiDirectoryPath"": {System.Text.Json.JsonSerializer.Serialize(pkiDir)}");
            if (IsOpcUaSecurityRun())
            {
                patched = System.Text.RegularExpressions.Regex.Replace(
                    patched,
                    @"""autoTrustCertificates""\s*:\s*(true|false)",
                    @"""autoTrustCertificates"": false");
            }
            File.WriteAllText(cfgPath, patched, System.Text.Encoding.UTF8);
        }

        return Path.Combine(tmpDir, Path.GetFileName(srcExePath));
    }

    private static void CopyDirectoryRecursive(string srcDir, string dstDir)
    {
        Directory.CreateDirectory(dstDir);
        foreach (var file in Directory.GetFiles(srcDir))
            File.Copy(file, Path.Combine(dstDir, Path.GetFileName(file)), overwrite: true);
        foreach (var subDir in Directory.GetDirectories(srcDir))
            CopyDirectoryRecursive(subDir, Path.Combine(dstDir, Path.GetFileName(subDir)));
    }

    private static void LogServerOutput(string line)
    {
        // Escalate the simulator's own long-path / MAX_PATH diagnostics to
        // Warning so they always surface in CI output, instead of being
        // silently dropped to Debug. Without this, a path-length cliff on
        // Windows runners is invisible until a downstream port-timeout
        // cascade buries the root cause.
        if (line.Contains("ERROR", StringComparison.OrdinalIgnoreCase)
            || line.Contains("WARNING", StringComparison.OrdinalIgnoreCase)
            || line.Contains("CRITICAL", StringComparison.OrdinalIgnoreCase)
            || line.Contains("Safe Threshold", StringComparison.OrdinalIgnoreCase)
            || line.Contains("Path Length", StringComparison.OrdinalIgnoreCase)
            || line.Contains("MAX_PATH", StringComparison.OrdinalIgnoreCase)
            || line.Contains("long path", StringComparison.OrdinalIgnoreCase))
        {
            _log.LogWarning("server stdout: {Line}", line);
            return;
        }

        _log.LogDebug("server stdout: {Line}", line);
    }

    private static string ResolveProjectTempRoot(string childDirectory)
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "IJT_CSharp_Client.csproj")))
                return Path.Combine(dir.FullName, "tmp", childDirectory);

            var projectRoot = Path.Combine(dir.FullName, "OPC_UA_Clients", "Release2", "IJT_CSharp_Client");
            if (File.Exists(Path.Combine(projectRoot, "IJT_CSharp_Client.csproj")))
                return Path.Combine(projectRoot, "tmp", childDirectory);

            dir = dir.Parent;
        }

        return Path.Combine(AppContext.BaseDirectory, "tmp", childDirectory);
    }

    /// <summary>
    /// Resolve a short root for ephemeral simulator artefacts (EXE copies, server
    /// PKI) on Windows. The project-nested default ("&lt;project&gt;/tmp/...")
    /// plus the GitHub Actions "D:\a\&lt;repo&gt;\&lt;repo&gt;\" workspace prefix can
    /// push simulator-generated cert filenames close to Windows MAX_PATH(260).
    /// The native simulator also emits path-length diagnostics before trust
    /// setup failures, so routing through RUNNER_TEMP (GitHub Actions =
    /// D:\a\_temp) gives the simulator and PKI directory layout predictable
    /// headroom without depending on long-path OS policy.
    ///
    /// On Linux paths are practically unbounded, so the project-local default
    /// is kept for repo-locality of artefacts.
    /// </summary>
    private static string ResolveShortFixtureRoot(string childDirectory)
    {
        if (!OperatingSystem.IsWindows())
            return ResolveProjectTempRoot(childDirectory);

        var runnerTemp = Environment.GetEnvironmentVariable("RUNNER_TEMP");
        var baseRoot = !string.IsNullOrWhiteSpace(runnerTemp) ? runnerTemp : Path.GetTempPath();
        return Path.Combine(baseRoot, "ijt-sim", childDirectory);
    }

    private static string ResolveShortServerPkiDirectory(int port)
    {
        var root = Environment.GetEnvironmentVariable("IJT_SERVER_PKI_ROOT");
        if (string.IsNullOrWhiteSpace(root))
            root = ResolveShortFixtureRoot("server-pki");

        var suffix = Guid.NewGuid().ToString("N")[..8];
        var pkiDir = Path.Combine(root, $"{port}_{suffix}");
        Directory.CreateDirectory(pkiDir);
        return pkiDir;
    }

    private static bool PreserveTestArtifacts()
        => string.Equals(Environment.GetEnvironmentVariable("IJT_PRESERVE_TEST_ARTIFACTS"), "1", StringComparison.OrdinalIgnoreCase)
           || string.Equals(Environment.GetEnvironmentVariable("IJT_PRESERVE_TEST_ARTIFACTS"), "true", StringComparison.OrdinalIgnoreCase)
           || string.Equals(Environment.GetEnvironmentVariable("IJT_PRESERVE_TEST_ARTIFACTS"), "yes", StringComparison.OrdinalIgnoreCase);

    public void Dispose()
    {
        if (_reusableSession is not null)
        {
            try
            {
                _reusableSession.DisposeAsync().AsTask().GetAwaiter().GetResult();
            }
            catch (Exception ex)
            {
                _log.LogWarning("Error closing reusable C# live-test session: {Message}", ex.Message);
            }
            finally
            {
                _reusableSession = null;
            }
        }

        _reusableSessionLock.Dispose();

        if (_serverProcess is not null)
        {
            try
            {
                if (!_serverProcess.HasExited)
                {
                    _serverProcess.Kill(entireProcessTree: true);
                    _serverProcess.WaitForExit(5000);
                }
            }
            catch (Exception ex) { _log.LogWarning("Error stopping server: {Message}", ex.Message); }
            finally { _serverProcess.Dispose(); }
        }

        if (_dockerStarted && !string.IsNullOrEmpty(_dockerComposeDir))
        {
            _log.LogInformation(
                "Stopping Docker OPC UA server ({Command})...",
                PreserveTestArtifacts() ? "docker compose down" : "docker compose down --volumes");
            try
            {
                var dockerExe = FindDockerExecutable();
                if (dockerExe is not null)
                {
                    using var r = new Process
                    {
                        StartInfo = new ProcessStartInfo
                        {
                            FileName = dockerExe,
                            Arguments = PreserveTestArtifacts() ? "compose down" : "compose down --volumes",
                            WorkingDirectory = _dockerComposeDir,
                            UseShellExecute = false,
                            CreateNoWindow = true,
                        },
                    };
                    r.StartInfo.Environment["OPCUA_SERVER_PORT"] = _port.ToString();
                    if (!string.IsNullOrWhiteSpace(_dockerComposeProjectName))
                        r.StartInfo.Environment["COMPOSE_PROJECT_NAME"] = _dockerComposeProjectName;
                    r.Start();
                    r.WaitForExit(30_000);
                }
            }
            catch (Exception ex) { _log.LogWarning("Error stopping Docker server: {Message}", ex.Message); }
        }

        if (_tempServerDir is not null)
        {
            if (PreserveTestArtifacts())
            {
                _log.LogInformation("Preserving temp server dir {Dir} because IJT_PRESERVE_TEST_ARTIFACTS is set.", _tempServerDir);
            }
            else
            {
                try { Directory.Delete(_tempServerDir, recursive: true); }
                catch (Exception ex) { _log.LogWarning("Error cleaning up temp server dir {Dir}: {Message}", _tempServerDir, ex.Message); }
            }
        }

        if (_tempServerPkiDir is not null)
        {
            if (PreserveTestArtifacts())
            {
                _log.LogInformation("Preserving temp server PKI dir {Dir} because IJT_PRESERVE_TEST_ARTIFACTS is set.", _tempServerPkiDir);
            }
            else
            {
                try { Directory.Delete(_tempServerPkiDir, recursive: true); }
                catch (Exception ex) { _log.LogWarning("Error cleaning up temp server PKI dir {Dir}: {Message}", _tempServerPkiDir, ex.Message); }
            }
        }

        if (ClientPkiRootPath is not null)
        {
            if (PreserveTestArtifacts())
            {
                _log.LogInformation("Preserving OPC UA security client PKI dir {Dir} because IJT_PRESERVE_TEST_ARTIFACTS is set.", ClientPkiRootPath);
            }
            else
            {
                try { Directory.Delete(ClientPkiRootPath, recursive: true); }
                catch (Exception ex) { _log.LogWarning("Error cleaning up OPC UA security client PKI dir {Dir}: {Message}", ClientPkiRootPath, ex.Message); }
            }
        }

        GC.SuppressFinalize(this);
    }
}
