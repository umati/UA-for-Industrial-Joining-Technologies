# Target Server CU Quick Start

## 1) Choose profile
- Remote start workflow: `target_server_cu_profiles/example_remote_start.yaml`
- Manual trigger workflow: `target_server_cu_profiles/example_manual_trigger.yaml`
- Simulator helper methods workflow: `target_server_cu_profiles/example_simulation_methods.yaml`
- New profile creation: copy from `target_server_cu_profiles/template.yaml`

## 2) Run commands
- Safe preflight check:
  `python run_target_server_cu.py --profile <profile>.yaml --preflight-only`
- Full automated run:
  `python run_target_server_cu.py --profile <profile>.yaml --mode automated`
- Guided/manual run with prompts:
  `python run_target_server_cu.py --profile <profile>.yaml --mode guided --interactive-prompts`

## 3) Read outputs
- `test-results/target-server-cu/target-server-cu-report.json` (machine-readable CU report)
- `test-results/target-server-cu/target-server-cu-summary.txt` (human-readable summary)
- `test-results/target-server-cu/spec-tests.xml` (CI/JUnit output)
