# EndpointGraphics Tab Adder

Implement tab additions in `src/javascripts/views/endpoint-tab/endpoint-graphics.mjs` using the project's manager-plus-view architecture.

## Key Principles

1. Reuse existing managers from `src/javascripts/ijt-support` first.
2. Add a new manager only when no existing manager fits.
3. Keep view logic in the view and transport/subscription logic in managers.
4. Preserve existing initialization order and guard patterns.

## Workflow

1. Choose a manager from `src/javascripts/ijt-support`:
   - Reuse an existing manager when it already provides the needed data.
   - Create a new manager only when no existing manager fits.
2. If creating a new manager, add `src/javascripts/ijt-support/feature-name/feature-name-manager.mjs` and export it from `src/javascripts/ijt-support/ijt-support.mjs`.
3. Create a new view file in `src/javascripts/views/feature-name/feature-name-graphics.mjs`.
4. Implement `constructor`, `initiate`, and `activate` in the new view class.
5. Import and instantiate the chosen manager + new view in `src/javascripts/views/endpoint-tab/endpoint-graphics.mjs`.
6. Register the tab with `tabGenerator.generateTab(viewInstance, level, selected?)`.
7. Preserve ordering conventions and view-level grouping.
8. Run lint to catch integration issues.

## Patterns To Reuse

### Manager source must be ijt-support (reuse first, then create if needed)
Reuse pattern:
```javascript
// EndpointGraphics.mjs imports
import { EventManager } from 'ijt-support/ijt-support.mjs'
```

New manager pattern (only if needed):
```javascript
// src/javascripts/ijt-support/my-feature/my-feature-manager.mjs
export class MyFeatureManager {
  constructor (connectionManager) {
    this.connectionManager = connectionManager
    this.callbacks = []
  }

  subscribe (callback) {
    this.callbacks.push(callback)
  }
}
```

```javascript
// src/javascripts/ijt-support/ijt-support.mjs
export { MyFeatureManager } from './my-feature/my-feature-manager.mjs'
```

### View must include constructor/initiate/activate
```javascript
// src/javascripts/views/my-feature/my-feature-graphics.mjs
import SingleScreen from '../graphic-support/single-screen.mjs'

export default class MyFeatureGraphics extends SingleScreen {
  constructor (myFeatureManager) {
    super('My Feature', 'MyFeature', 'myfeature')
    this.myFeatureManager = myFeatureManager
  }

  initiate () {
    // build initial DOM state and subscriptions
  }

  activate (state) {
    // react to tab activation state changes
  }
}
```

### EndpointGraphics wiring
```javascript
// imports
import { MyFeatureManager } from 'ijt-support/ijt-support.mjs'
import MyFeatureGraphics from 'views/my-feature/my-feature-graphics.mjs'

// inside instantiate(...)
const myFeatureManager = new MyFeatureManager(this.connectionManager)
const myFeatureGraphics = new MyFeatureGraphics(myFeatureManager)
tabGenerator.generateTab(myFeatureGraphics, 3)
```

### Optional tab safety pattern
```javascript
let optionalGraphics = null
try {
  optionalGraphics = new OptionalGraphics(dependencyA, dependencyB)
} catch (error) {
  console.log(error)
}

if (optionalGraphics) {
  tabGenerator.generateTab(optionalGraphics, 3)
}
```

## View-Level Guidance

- Level `1`: demo or operator-first flows.
- Level `2`: primary runtime interaction tabs.
- Level `3`: secondary/reference views.
- Level `4+`: heavier or less frequently used tabs.

Use nearby existing tabs as the source of truth when uncertain.

## Safety Rules

1. Keep initialization order valid; do not use managers before they are created.
2. Route new tab data through a manager from `ijt-support`; prefer existing managers before adding new ones.
3. Ensure each created view file defines `constructor`, `initiate`, and `activate`.
4. Do not access raw socket logic directly from the view.
5. Do not remove existing guards unless explicitly requested.
6. Keep dynamic import blocks (like `Envelope`) intact unless the request targets them.
7. Prefer minimal diffs and preserve existing naming/style conventions.

## Completion Checklist

1. Confirm a manager from `ijt-support` is used (existing preferred; new only if justified).
2. If a new manager was added, confirm it exists in `src/javascripts/ijt-support/feature-name/` and is exported from `ijt-support.mjs`.
3. Confirm new view file exists in `src/javascripts/views/feature-name/` with `constructor`, `initiate`, and `activate`.
4. Confirm `EndpointGraphics.mjs` imports and constructs the manager and view with valid dependencies.
5. Confirm `tabGenerator.generateTab(...)` is called with intended level and optional selection flag.
6. Run `npm run lint` from project root.
7. Summarize what manager source was used, what view was added, and how tab wiring was updated.
