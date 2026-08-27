# IJT Test Client + OPC UA Server Integration Summary

## 1) What this is in simple words
The **IJT Test Client** is a checker that verifies whether an OPC UA IJT Server follows the IJT specification correctly.
It does **not** replace a simulator. It adds a formal, repeatable conformance check.

- **Simulator** = functional behavior testing
- **IJT Test Client** = specification conformance testing (CUs)

Together, they give confidence for release and customer interoperability.

## 2) What "123 CUs" means
- The project is built around **123 official IJT Conformance Units (CUs)**.
- The test framework and CU reporting are designed to cover this full official set.
- Run output should always clearly classify each CU (not just pass/fail).

Goal: **all CUs executed and clearly classified**, every run.

## 3) Why there are many test folders
This is normal and intentional.

- `specification_tests` = the main specification test suite (the main container)
- folders like `results`, `assets`, `joining_process`, `common` = topic groups (chapters) inside that suite

It is not duplicate testing; it is organized by feature domain.

## 4) How YAML profiles are used
YAML profiles tell the runner **how to test a specific target server**.

Use from command line:

- Safe check first
  `python run_target_server_cu.py --profile <profile>.yaml --preflight-only`
- Full run
  `python run_target_server_cu.py --profile <profile>.yaml --mode automated`
- Guided/manual flow when needed
  `python run_target_server_cu.py --profile <profile>.yaml --mode guided --interactive-prompts`

Profile examples:

- `example_multi_operation_job.profile.yaml` (complete automated controller workflow)
- `example_multi_operation_job.capabilities.yaml` (paired CU declaration)
- `example_manual_trigger.profile.yaml` (operator/manual trigger)
- `example_simulation_methods.profile.yaml` (simulation helper methods)
- `template.profile.yaml` (base template)

## 5) What is default behavior today
- Default test flow remains the normal simulator-based path.
- Target-server CU profile flow is **opt-in** via `--profile`.
- Root runner can include non-blocking target-server preflight when requested.

Existing flow stays stable; target-server profile flow is an additional controlled path.

## 6) Integration focus when only controller mapping differs
If simulator code and controller server code are the same, with only controller API mapping differences, integration risk is mainly in **configuration + timing + trigger mode**, not namespace/model shape.

Most important profile settings:

1. endpoint
2. trigger mode (remote start vs manual)
3. allowed state-changing methods
4. timeout values
5. selection policy (tool/process discovery vs exact IDs)

## 7) Standard CU output language
For every CU in every run, show one clear status:

1. **Supported/Pass** - executed and passed
2. **Not Supported** - outside declared server capability
3. **Blocked** - could not run due to precondition/setup dependency
4. **Failed** - executed but behavior incorrect
5. **Environment/Error** - tooling/network/environment issue

This avoids ambiguity and makes reports easy to understand.

## 8) Current operating status and maintenance
No major reorganization is required.

Current baseline in this project:

1. Full CU-oriented reporting is already in place through the standard report outputs.
2. Capability declarations are already part of the supported/not-supported classification flow.
3. Timeout and trigger settings are already configurable per target profile and can be tuned per endpoint.
4. Ongoing maintenance is to keep profile values and capability declarations aligned with real server behavior.

## 9) Summary
"The IJT Test Client already provides full IJT CU framework coverage; the operational focus is consistent all-CU execution with clear, auditable CU-by-CU outcomes for releases."
