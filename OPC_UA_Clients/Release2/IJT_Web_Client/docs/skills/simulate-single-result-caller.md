# SimulateSingleResult Caller

Implement consistent `SimulateSingleResult` invocation using existing method infrastructure in `MethodGraphics`, `MethodGUICreator`, `MethodManager`, and `src/Resources/settings.json`.

## Input Arguments

Use this interpretation for the first input argument (result scenario):

- `0`: simple OK result
- `1`: single-step OK result (default)
- `2`: multi-step OK result
- `3`: multi-step NOK result
- `4`: multi-step NOK result with trigger-lost flag set

The second input argument is a boolean for including traces:

- `false` (default): do not include traces
- `true`: include traces

Prefer scenario `1` for default behavior. Use `3` when a NOK default is explicitly needed.

## Workflow

1. Verify method discovery includes the SimulateResults folder in `src/Javascripts/Views/Methods/MethodGraphics.mjs`.
2. Verify or update defaults for `ns=1;s=TighteningSystem/Simulations/SimulateResults/SimulateSingleResult` in `src/Resources/settings.json`.
3. Use the existing Methods tab call pipeline:
   - `MethodGUICreator.createMethodArea(...)` builds inputs and Call button.
   - `MethodManager.call(...)` sends the OPC UA method call.
4. If requested, trigger the call from UI defaults by setting `autocall` for the method in `settings.json`.
5. Keep all changes minimal and aligned with current method invocation patterns.
6. Run lint after edits.

## Source-of-Truth Files

- `src/Javascripts/Views/Methods/MethodGraphics.mjs`
- `src/Javascripts/Views/Methods/MethodGUICreator.mjs`
- `src/Javascripts/ijt-support/Methods/MethodManager.mjs`
- `src/Resources/settings.json`

## Required Checks

1. Confirm the method folder path includes:
   - `Simulations`
   - `SimulateResults`
2. Confirm the node id key exists in `settings.json`:
   - `ns=1;s=TighteningSystem/Simulations/SimulateResults/SimulateSingleResult`
3. Confirm argument defaults match expected datatypes before enabling `autocall`.

## Common Tasks

### Add or adjust defaults

Edit this block in `src/Resources/settings.json`:

```json
"ns=1;s=TighteningSystem/Simulations/SimulateResults/SimulateSingleResult": {
  "arguments": [1, false],
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
