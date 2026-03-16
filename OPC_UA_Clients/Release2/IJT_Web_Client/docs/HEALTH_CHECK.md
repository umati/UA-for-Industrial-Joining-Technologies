# Health Check
Run these before and after code changes:

```bash
npm run lint
venv\Scripts\python.exe -m pip check
venv\Scripts\python.exe index.py
npm run start
```

Expected results:
- `npm run lint` exits with code 0.
- `pip check` reports no broken requirements.
- Backend starts and logs WebSocket startup on port `8001`.
- Frontend responds on `http://localhost:3000`.