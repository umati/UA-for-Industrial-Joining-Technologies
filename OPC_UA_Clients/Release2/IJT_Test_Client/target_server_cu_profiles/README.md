# Target Server CU Profiles

This directory contains execution profiles (`*.profile.yaml`) and capability declarations (`*.capabilities.yaml`) for validating OPC UA Industrial Joining Technologies (IJT) servers under test (SUT) against OPC 40450-1 (Release 2.0).

For the complete manual on server integration, process selection, layered results, and safety rules, see the **[Target Server CU Guide](../docs/TARGET_SERVER_CU_GUIDE.md)**.

---

## File Naming Convention

| File Type | Suffix | Responsibility | Tester Normally Edits? |
|---|---|---|:---:|
| **Execution Profile** | `*.profile.yaml` | Endpoint, timeouts, process/tool selection, trigger mode, allowed methods | Yes |
| **Capability Declaration** | `*.capabilities.yaml` | Declared Conformance Unit (CU) support matrix (`supported`, `unsupported`, `manual_required`) | Yes |
| **Internal Spec Catalog** | `profiles/*.yaml` | Official OPC UA IJT profile and facet definitions | No |

---

## Profile Catalog

| File | Purpose |
|---|---|
| [`template.profile.yaml`](template.profile.yaml) | Universal execution profile template with all supported schema fields and safe defaults |
| [`default.capabilities.yaml`](default.capabilities.yaml) | Default capability matrix used when no specific capability file is selected |
| [`simulator.capabilities.yaml`](simulator.capabilities.yaml) | Full capability declaration matching the built-in OPC UA IJT simulator |
| [`example_multi_operation_job.profile.yaml`](example_multi_operation_job.profile.yaml) | Complete automated controller example: ID-first selection, layered results, and safe enablement |
| [`example_multi_operation_job.capabilities.yaml`](example_multi_operation_job.capabilities.yaml) | Paired capability declaration for the automated controller workflow |
| [`example_manual_trigger.profile.yaml`](example_manual_trigger.profile.yaml) | Example for controllers requiring a physical tool trigger / manual operator cycle |
| [`example_simulation_methods.profile.yaml`](example_simulation_methods.profile.yaml) | Example for servers exposing simulation helper methods |

---

## Quick Start Cheat-Sheet

All commands run via `run_all_tests.py` from `OPC_UA_Clients/Release2/IJT_Test_Client`:

```bash
# 1. Auto-discover target server tools and processes (emits suggested YAML):
python run_all_tests.py --endpoint opc.tcp://<host>:40451 --discover-target

# 2. Safe preflight check (validates configuration & TCP; no state changes):
python run_all_tests.py --preflight-only --profile target_server_cu_profiles/my_profile.yaml

# 3. Full validation run (Phase 1 quality + preflight + live specification tests + evidence):
python run_all_tests.py --profile target_server_cu_profiles/my_profile.yaml --spec-tests-timeout 3600

# 4. Specification tests only (skips Phase 1 static analysis):
python run_all_tests.py --phase2 --profile target_server_cu_profiles/my_profile.yaml --spec-tests-timeout 3600
```

---

## Learn More

- **[Target Server CU Guide](../docs/TARGET_SERVER_CU_GUIDE.md)** — complete guide on architecture, controller setup, execution recipes, process selection, result layering & safety semantics
- **[Reporting Glossary & KPIs](../docs/REPORT_GLOSSARY.md)** — metric definitions, outcome statuses, and report contracts
- **[Test Report Formats](../docs/test-results.md)** — JSON schemas, JUnit XML, and Excel generation
