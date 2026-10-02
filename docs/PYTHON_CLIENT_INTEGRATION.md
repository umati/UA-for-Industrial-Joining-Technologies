# Integrating the Python Clients

This guide covers the Release 2 Console, Test, Performance, and Web clients.
Use each client's README for normal setup and usage. Their setup/test launchers
prepare dependencies automatically; manual dependency management is optional.

## Choose Your Approach

| Need | Approach |
|------|----------|
| Run the reference client or its tests | Use the README commands in a full repository checkout. |
| Deploy into an existing pip-managed environment | Prepare a requirements export from the client's lock, then install it with the destination environment's Python. |
| Reuse source code in your own application | Install the needed dependencies and account for the client's source files, configuration, assets, and shared modules. Dependency installation alone does not make a client portable. |
| Change dependencies | Update the client's `pyproject.toml`, regenerate `uv.lock`, and validate the affected client. See [Development](DEVELOPMENT.md). |

Python 3.14+ is required. The Web Client also needs Node.js 24.15+ for its frontend.
Docker and .NET are separate prerequisites only for the components/checks that
use them. Git is needed for repository checks and commit hooks.

## Pip-Based Deployment

**The destination system does not need uv.** A developer or build system uses
uv to export reviewed dependency pins once; the destination installs that
artifact using standard pip. Exports are generated artifacts, not a second
dependency source to maintain in this repository.

The repository does not include pre-generated requirements exports. If your
organisation does not use uv on destination machines, produce the export in
your build/release pipeline and distribute it with the matching source revision.
If uv is prohibited everywhere, there is currently no documented pip-only
conversion of `uv.lock`; do not rename the lock or treat it as a pip requirements
file.

### Prepare the Dependency Artifact

Run from the affected client directory, using the reviewed uv version. You can
install uv in a separate tooling environment or use the executable prepared
under that client's `.state/tools/` by its setup/test launcher.

For Console, Web, or Performance runtime dependencies:

```bash
uv lock --check
uv export --frozen --no-dev --no-emit-project -o runtime-requirements.txt
```

The Test Client executes pytest-based specification tests. Runtime dependencies
alone are not enough; export its development/test group too:

```bash
uv lock --check
uv export --frozen --all-groups --no-emit-project -o test-requirements.txt
```

Use the same all-groups export for another client's contributor/test environment.
`--frozen` exports the existing lock rather than updating it; `uv lock --check`
first verifies that it matches the manifest. Keep the export's hashes and
environment markers. Validate each destination OS and Python version separately.

Do not commit these exports or edit their pins by hand. Regenerate them from
the lock when releasing a different source revision.

### Install with Pip

Create a separate environment, or select your organisation's existing isolated
environment. Do not install into global Python:

```bash
python -m venv .venv_integration
```

Set `PYTHON` to that environment's interpreter:

```powershell
# Windows PowerShell
$PYTHON = ".\.venv_integration\Scripts\python.exe"
& $PYTHON -m pip install --require-hashes -r runtime-requirements.txt
& $PYTHON -m pip check
```

```bash
# Linux / macOS
PYTHON=./.venv_integration/bin/python
"$PYTHON" -m pip install --require-hashes -r runtime-requirements.txt
"$PYTHON" -m pip check
```

For the Test Client or contributor tests, substitute `test-requirements.txt`.
Pip installs the Python packages; it does not install application source,
frontend packages, configuration, or simulator binaries.

For offline deployment, prepare an approved wheelhouse for the destination
platform and use pip's `--no-index --find-links` options. A requirements export
alone does not contain the packages.

### Keep the Lock Guarantees

The clients' uv configuration also contains dependency constraints. Pip does
not enforce `[tool.uv]` settings when installing project metadata directly.
Installing only the top-level packages, or using `pip install .` with normal
dependency resolution, is **not equivalent** to installing the reviewed export.

If your application already has dependencies, resolve and validate conflicts
explicitly. Do not suppress a conflict using `--no-deps` for third-party packages.
The Performance Client's source installation below uses `--no-deps` only after
its complete exported dependency set has been installed.

## Client-Specific Integration

### Console Client

After installing the runtime export, run with your selected interpreter from
the Console Client directory:

```powershell
& $PYTHON main.py --url="opc.tcp://localhost:40451"
```

On POSIX use `"$PYTHON" main.py --url="opc.tcp://localhost:40451"`.
See `client_config.py` and [Features](../OPC_UA_Clients/Release2/IJT_Console_Client/docs/FEATURES.md)
for configuration and supported operations.

### Test Client

Use the README's `run_all_tests.py` commands for the supported end-to-end
specification workflow, including controller profiles, reporting, and simulator
handling. Those commands manage their own environment; exporting requirements
does not change that behaviour.

For custom pytest integration, install the test export and retain the client
fixtures, profiles, and repository layout. Follow the
[Target Server CU Guide](../OPC_UA_Clients/Release2/IJT_Test_Client/docs/TARGET_SERVER_CU_GUIDE.md)
for applicability and safety. A bare pytest invocation is not a replacement
for the runner's complete profile/preflight/reporting workflow.

### Performance Client

After installing the runtime export, `main.py` can run against an existing
server using your selected interpreter. See the README for benchmark options.

This is the packaged client. If you need its `ijt-perf` console command, also
install the client source from its directory:

```powershell
& $PYTHON -m pip install --no-deps .
```

On POSIX use `"$PYTHON" -m pip install --no-deps .`. Pip's build isolation may
need access to the declared build dependencies; provision those separately for
an offline build. The exported dependency file deliberately omits the project
itself. Keep profile files available when using source-based examples.

### Web Client

The Python runtime export covers the backend only. Keep the Web Client source,
resources, and configuration, and install the frontend's locked dependencies
from its directory:

```bash
npm ci --legacy-peer-deps
```

Use the [Development Guide](../OPC_UA_Clients/Release2/IJT_Web_Client/docs/DEVELOPMENT_GUIDE.md)
for backend/frontend startup, and
[Configuration](../OPC_UA_Clients/Release2/IJT_Web_Client/docs/CONFIGURATION.md)
for connection settings. The setup launcher manages its own Python environment;
do not assume it will use your pip environment.

## Source Layout and Shared Modules

**Keep the full checkout for the supported reference workflows.** Console,
Test, and Web use the root-level `scripts/opcua_session_policy_loader.py` and
`scripts/opcua_session_policy.py` for consistent OPC UA sessions. Some imports
still depend on the repository's directory depth. Adding those files to an
arbitrary directory or setting `PYTHONPATH` alone is not a verified standalone
deployment recipe.

Setup/test launchers also use `scripts/tool_bootstrap.py` and repository-level
test configuration; live tests may need simulator assets. Performance's fleet
launcher needs simulator assets as well. These are distinct from runtime
Python dependencies.

When extracting code into another system, inventory the imports and non-Python
assets, adapt layout-dependent imports deliberately, and test connection,
reconnection, cleanup, and result handling in that system. These reference
clients are not all independently installable pip packages.

## Documentation Boundaries

READMEs describe user prerequisites, automatic launchers, normal usage, and
links to integration guidance. This guide describes deployment choices and
their guarantees. Client `docs/SKILLS.md` files describe contributor architecture,
internal tooling, and coding/test rules; they are not required onboarding steps
for end users.
