# IJT Test Client

IJT specification test client for specification testing of OPC UA IJT servers against the Industrial Joining Technologies companion specifications.

## Contact

- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Prerequisites

- Python 3.14+
- Internet connection for first-time dependency installation
- An OPC UA IJT server for specification tests: use the checked-in simulator or your own controller

**Default endpoint:** `opc.tcp://localhost:40451`

## Quick Start

Run these commands from this client directory. The runner prepares Python
dependencies and uv automatically in isolated environments.
No manual uv installation or shell activation is needed.

```bash
python run_all_tests.py
```

`run_all_tests.py` is the single documented entry point for this test client — it
runs static analysis, then the full specification_tests/ suite against either the
checked-in simulator (auto-launched) or a real Target Server, if configured. Both
are "OPC UA Servers Under Test": they run the identical specification suite. A
Target Server CU profile only controls applicability, safety, scoring, and
evidence — never a separate test suite.

See [Target Server CU Guide](docs/TARGET_SERVER_CU_GUIDE.md) for the
full Target Server option reference.

## Usage

### Testing a Real Controller

**Every run — one command:**
```bash
python run_all_tests.py run --profile target_server_cu_profiles/controller_remote_start.sut.yaml --endpoint opc.tcp://<host>:40451
```

Use [`controller_manual_trigger.sut.yaml`](target_server_cu_profiles/controller_manual_trigger.sut.yaml) instead if the operator physically triggers the tool.

**Only create a custom manifest** when the target controller has different capability claims. Use `init-profile` to auto-generate one from live discovery:
```bash
python run_all_tests.py init-profile --endpoint opc.tcp://<host>:40451 --output controller.sut.yaml
```

Optional read-only discovery (safe, no state change, no manifest needed):
```bash
python run_all_tests.py inspect --endpoint opc.tcp://<host>:40451
```

To check profile classification before executing specification tests:

```bash
python run_all_tests.py run --profile controller.sut.yaml --endpoint opc.tcp://<host>:40451 --preflight-only
```

If recreating controller programs or sequences makes an exact process selector
stale, refresh the existing local manifest instead of copying IDs by hand:

```bash
python run_all_tests.py refresh-profile --profile controller.sut.yaml
```

The guide reads the profile's live catalog using its security settings, groups
matching Job/counter/parent references, and asks you to choose a current process.
It honors a configured non-first Tool and refuses missing/ambiguous Tool
identities. Keeping a match also checks its required secondary identifiers;
selection-name-only targets must have a unique wire name.
All advertised selection-name aliases are displayed. An existing advertised
alias is retained; a sole alias can be refreshed automatically, but multiple
aliases require an explicit advertised name if the profile uses or stores one.
Secondary-only references group only when both active matching keys are shared.
Review the identifier-only diff and type the displayed confirmation to save.
Comments, exact-match policies, identifier strategies, claims and approvals stay
unchanged. No joining, counter or test workload runs; cancel leaves the file
unchanged. Use an interactive terminal and a previously prepared environment.

Blocked setup names the actual profile, effective endpoint and manifest field
in the terminal and text/Markdown summaries. Use its preflight-only recheck;
refresh is suggested for stale selectors, not connection/security failures.
Never weaken exact selectors, CU claims or approvals just to pass preflight.

Follow the guide's safety and applicability instructions before testing a
physical controller; choose the profile that matches its capabilities and
trigger mode.

## Testing

```bash
python run_all_tests.py --phase1   # static checks and unit tests; no server needed
python run_all_tests.py --phase2   # specification tests; simulator or configured server
```

Some specification tests apply only to the IJT simulator and are skipped for
other servers; see [regression contracts](docs/SKILLS.md#result-trace-and-stateful-regression-contracts).

## Integration

Using pip or integrating specification tests into your own validation system?
See the [Python Client Integration Guide](../../../docs/PYTHON_CLIENT_INTEGRATION.md).
This client needs test dependencies, shared repository fixtures/modules, and
profile/reporting configuration; a runtime-only install is insufficient.

## Learn More

- [Target Server CU Guide](docs/TARGET_SERVER_CU_GUIDE.md) — complete guide: architecture, controller setup, execution recipes, process selection, result layering & safety semantics
- [Reporting Glossary & KPIs](docs/REPORT_GLOSSARY.md) — metrics definitions, status codes & report contracts
- [Developer Guide & Coding Rules](docs/SKILLS.md) — architecture, zero-escape gates & async rules
- [Test Report Formats](docs/test-results.md) — output files, JSON schemas & Excel generation
- [Target Server CU Profiles](target_server_cu_profiles/README.md) — profile inventory & template catalog
