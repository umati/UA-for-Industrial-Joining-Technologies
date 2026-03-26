# IJT Support Agent Guide

This guide gives agents a quick map of the `ijt-support` library and how to change it safely.

## What `ijt-support` Does

`ijt-support` is the client-side core library for:
- WebSocket communication with the Python backend,
- OPC UA request/response flow handling,
- model parsing and typing,
- managers for results, methods, entities, assets, and events.

It is imported in `index.html` through:
- `Javascripts/ijt-support/ijt-support.mjs`

## High-Level Flow

1. Browser creates `WebSocketManager`.
2. UI sends commands (`connect to`, `read`, `browse`, `methodcall`, etc.).
3. Python backend handles OPC UA communication.
4. Responses/events return over WebSocket.
5. `ModelManager` converts payloads into typed models.
6. UI managers/views consume typed data.

## Important Areas

- `Connection/`:
  transport layer (`WebSocketManager`, `SocketHandler`, `ConnectionManager`).
- `Models/`:
  typed model system (see `docs/guides/models-guide.md`).
- `Results/`, `Events/`, `Methods/`, `Assets/`, `EntityCache/`, `Joints/`:
  domain managers and support logic used by views.
- `Settings/`:
  app-level config helpers and persistence interactions.

## Core Contracts Agents Must Preserve

- WebSocket command names and payload structure.
- ModelManager factory behavior and cast mappings.
- Linked references used by result/trace models.
- Manager callback/subscription behavior.

If these contracts change, dependent UI code usually breaks.

## Safe Edit Checklist

Before editing:
- Identify which manager/view depends on your target module.
- Confirm command/event names used across JS and Python.

After editing:
- Run `npm run lint`.
- Start backend and frontend.
- Verify:
  - page loads,
  - websocket connects,
  - at least one endpoint can connect,
  - result/trace view still updates.

## Recommended Agent Workflow

1. Make minimal targeted changes.
2. Prefer adding/adjusting mappings over ad-hoc parsing in views.
3. Keep backward compatibility unless explicitly requested.
4. Report changed files + behavior impact + residual risk.

## Useful Companion Docs

- `docs/guides/models-guide.md`
- `docs/guides/result-model-guide.md`
