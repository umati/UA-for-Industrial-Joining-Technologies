---
name: simulate-single-result-caller
description: Invoke or wire the SimulateSingleResult OPC UA method in IJT Web Client. Use when requests ask to call, expose, debug, or preconfigure `SimulateSingleResult` through the Methods view, method defaults, or method folder discovery.
---

# SimulateSingleResult Caller

Implement consistent `SimulateSingleResult` invocation using existing method infrastructure in `MethodGraphics`, `MethodGUICreator`, `MethodManager`, and `Resources/settings.json`.
The first argument can have the following values:
0 for a simple OK result
1 for a single step OK result
2 for a multistep OK result
3 for a multistep NOK, not OK result
4 for multiple steps NOK result with "trigger lost" flag set
The default should be 1, but if it is supposed to be a not OK result, 3 should be set
The second argument is a boalean determining if traces should be included in the result. The default value should be not to include traces 

## Workflow

1. Verify method discovery includes the SimulateResults folder in `Javascripts/Views/Methods/MethodGraphics.mjs`.
2. Verify or update defaults for `ns=1;s=TighteningSystem/Simulations/SimulateResults/SimulateSingleResult` in `Resources/settings.json`.
3. Use the existing Methods tab call pipeline:
   - `MethodGUICreator.createMethodArea(...)` builds inputs and Call button.
   - `MethodManager.call(...)` sends the OPC UA method call.
4. If requested, trigger the call from UI defaults by setting `autocall` for the method in `settings.json`.
5. Keep all changes minimal and aligned with current method invocation patterns.
6. Run lint after edits.

## Source-of-Truth Files

- `Javascripts/Views/Methods/MethodGraphics.mjs`
- `Javascripts/Views/Methods/MethodGUICreator.mjs`
- `Javascripts/ijt-support/Methods/MethodManager.mjs`
- `Resources/settings.json`

## Required Checks

1. Confirm the method folder path includes:
   - `Simulations`
   - `SimulateResults`
2. Confirm the node id key exists in `settings.json`:
   - `ns=1;s=TighteningSystem/Simulations/SimulateResults/SimulateSingleResult`
3. Confirm argument defaults match expected datatypes before enabling `autocall`.

## Common Tasks

### Add or adjust defaults

Edit this block in `Resources/settings.json`:

```json
"ns=1;s=TighteningSystem/Simulations/SimulateResults/SimulateSingleResult": {
  "arguments": [2, true],
  "autocall": false
}
```

Use only values that map to the method's current input argument schema.

### Ensure method appears in Methods tab

Confirm `activate()` in `MethodGraphics.mjs` includes the SimulateResults folder path in `methodFolders` and keeps `setupMethodsInFolders(...)` flow intact.

### Diagnose call failures

1. Check method exists in `methodManager.getMethodNames()`.
2. Check defaults in `settings.json` for invalid type/value shapes.
3. Check call output from `MethodGUICreator` message display.
4. Check backend connection/subscription status from Connection tab.

## Safety Rules

1. Reuse existing method pipeline; do not bypass `MethodManager.call(...)`.
2. Avoid changing generic datatype casting in `MethodManager.call(...)` unless explicitly requested.
3. Keep `autocall` disabled by default unless the user asks for automatic invocation.
4. Preserve unrelated method defaults and folder discovery entries.

## Completion Checklist

1. Confirm `SimulateSingleResult` can be discovered in Methods tab.
2. Confirm invocation works with configured defaults.
3. Confirm lint passes.
4. Summarize exactly what was changed in method discovery/defaults/call behavior.
