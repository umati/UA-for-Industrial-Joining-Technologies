export function createOptionalTraceExtensionLoader (modulePath, fallbackModule = {}) {
  let activeModule = fallbackModule
  let loadAttempted = false

  const tryLoad = () => {
    if (loadAttempted) {
      return
    }
    loadAttempted = true

    import(modulePath).then((module) => {
      activeModule = {
        ...fallbackModule,
        ...module,
      }
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
      return activeModule
    }
  }
}
