# Health Check

Run these before and after code changes:

```bash
npx eslint src/javascripts config.js --config eslint.config.mjs --max-warnings 0
python -m pip check
python index.py
```

Expected results:
- ESLint exits with code 0, 0 warnings.
- `pip check` reports no broken requirements.
- Backend starts and logs WebSocket startup on port `8001`.
- Frontend responds on `http://localhost:3000`.

## Quick Full Test Run
```bash
python run_all_tests.py
```
Expected: ~128 Python pass, 70 JS pass, 0 lint errors.
(Live OPC UA tests in `tests/test_opcua_methods.py` require a running server on `opc.tcp://localhost:40451`.)