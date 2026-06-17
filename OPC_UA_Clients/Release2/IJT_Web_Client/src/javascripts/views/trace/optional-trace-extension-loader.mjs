const extensionStates = new Map()

export function createOptionalTraceExtensionLoader (modulePath, fallbackModule = {}) {
  let state = extensionStates.get(modulePath)
  if (!state) {
    state = {
      activeModule: fallbackModule,
      fallbackModule,
      loadAttempted: false,
      loaded: false,
      callbacks: new Set()
    }
    extensionStates.set(modulePath, state)
  } else if (!state.loaded) {
    state.fallbackModule = {
      ...fallbackModule,
      ...state.fallbackModule
    }
    state.activeModule = {
      ...fallbackModule,
      ...state.activeModule
    }
  }

  const tryLoad = () => {
    if (state.loadAttempted) {
      return
    }
    state.loadAttempted = true

    import(modulePath).then((module) => {
      state.activeModule = {
        ...state.fallbackModule,
        ...module,
      }
      state.loaded = true
      for (const callback of state.callbacks) {
        callback(state.activeModule)
      }
      state.callbacks.clear()
    }).catch(() => {
      // Optional extension: keep fallback module when extension is absent.
    })
  }

  return {
    get () {
      // Lazy: attempt load on first access rather than at module-init time.
      // This prevents a 404 network request during initial page load when the
      // extension file does not yet exist, while still loading it once available.
      tryLoad()
      return state.activeModule
    },
    onLoad (callback) {
      if (typeof callback !== 'function') {
        return () => {}
      }
      if (state.loaded) {
        callback(state.activeModule)
        return () => {}
      }
      state.callbacks.add(callback)
      tryLoad()
      return () => {
        state.callbacks.delete(callback)
      }
    }
  }
}
