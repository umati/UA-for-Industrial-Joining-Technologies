# Views Agent Guide

This guide helps agents understand how the `Javascripts/Views` layer is organized and how to edit it safely.

## Purpose

The `Views` folder contains UI screens and UI helpers that:
- render data from `ijt-support` managers/models,
- trigger connection/read/browse/method actions,
- visualize results/traces/envelope checks.

## Core Pattern

Most screens extend `GraphicSupport/BasicScreen.mjs`.

Typical lifecycle:
1. `constructor(...)` builds static DOM containers and stores manager references.
2. `activate()` builds/initializes interactive UI areas.
3. `initiate()` runs each time tab/screen is opened.
4. event handlers update UI and call manager methods.

Tabs are managed by `GraphicSupport/TabGenerator.mjs`.

## Main View Groups

- `Servers/`:
  endpoint list and connect/disconnect flow.
- `EndpointTab/`:
  endpoint-specific tab composition.
- `AddressSpace/`:
  browse/read visualization of the address space
- `Methods/`:
  method invocation UI.
- `Trace/`:
  chart rendering, zoom, and interaction.
- `Envelope/`:
  limit/selection configuration and validation overlays.
- `Demo/`:
  demo screens for joint/program/result usage.
- `ComplexResult/`:
  hierarchical/enveloped result rendering of batches and jobs.
- `Assets/`, `Entities/`, `Joints/`:
  domain-focused editing and visualization screens.
- `GraphicSupport/`:
  reusable UI primitives (tabs, basic controls, settings).

## Styling Rules (current project)

- Use CSS classes in `nodeStyle.css` for static styling.
- Keep inline style only for truly dynamic positioning/sizing (e.g., drag overlay pixel positions).
- Reuse existing utility/layout classes when possible.

## Safe Edit Rules

- Do not break `BasicScreen` API expectations (`activate`, `initiate`, `close` patterns).
- Keep tab selection behavior compatible with `TabGenerator`.
- Preserve manager callback wiring (`subscribe(...)`) and event propagation.
- Prefer minimal view-local changes; avoid moving protocol/model logic into views.

## Common Agent Tasks

- Move static inline styles to CSS classes.
- Fix UI rendering issues without changing data contracts.
- Improve layout readability and consistency.
- Add small UX safeguards (empty-state checks, null guards).

## Validation Checklist

After view edits:
- `npm run lint` passes.
- App opens at `http://localhost:3000`.
- WebSocket backend is reachable.
- Key screens still open and render:
  - Servers
  - Endpoint tabs
  - Trace/Envelope
  - Demo screens

## Related Docs

- `docs/guides/ijt-support-guide.md`
- `docs/guides/models-guide.md`
- `docs/guides/result-model-guide.md`
