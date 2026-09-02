# IJT Test Client

IJT specification test client for specification testing of OPC UA IJT servers against the Industrial Joining Technologies companion specifications.

## Contact

- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Prerequisites

- Python 3.14+
- Internet connection for first-time dependency installation
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2)

**Default endpoint:** `opc.tcp://localhost:40451`

## Quick Start

```bash
python run_all_tests.py
```

`run_all_tests.py` is the single documented entry point for this test client — it
runs static analysis, then the full specification_tests/ suite against either the
checked-in simulator (auto-launched) or a real Target Server, if configured. Both
are "OPC UA Servers Under Test": they run the identical specification suite. A
Target Server CU profile only controls applicability, safety, scoring, and
evidence — never a separate test suite.

```bash
python run_all_tests.py                                        # Phase 1 + Phase 2 (simulator auto-launch)
python run_all_tests.py --phase1                               # static analysis only
python run_all_tests.py --phase2                               # specification_tests only
python run_all_tests.py inspect --endpoint opc.tcp://<host>:40451          # read-only discovery (no state change)
python run_all_tests.py init-profile --endpoint opc.tcp://<host>:40451 --output controller.sut.yaml  # guided manifest creation
python run_all_tests.py run --profile target_server_cu_profiles/controller_remote_start.sut.yaml --endpoint opc.tcp://<host>:40451  # full controller run
python run_all_tests.py run --profile controller.sut.yaml --endpoint opc.tcp://<host>:40451 --preflight-only  # classification only
```

See [Target Server CU Guide](docs/TARGET_SERVER_CU_GUIDE.md) for the
full Target Server option reference.

## Testing a Real Controller

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

## Learn More

- [Target Server CU Guide](docs/TARGET_SERVER_CU_GUIDE.md) — complete guide: architecture, controller setup, execution recipes, process selection, result layering & safety semantics
- [Reporting Glossary & KPIs](docs/REPORT_GLOSSARY.md) — metrics definitions, status codes & report contracts
- [Developer Guide & Coding Rules](docs/SKILLS.md) — architecture, zero-escape gates & async rules
- [Test Report Formats](docs/test-results.md) — output files, JSON schemas & Excel generation
- [Target Server CU Profiles](target_server_cu_profiles/README.md) — profile inventory & template catalog
