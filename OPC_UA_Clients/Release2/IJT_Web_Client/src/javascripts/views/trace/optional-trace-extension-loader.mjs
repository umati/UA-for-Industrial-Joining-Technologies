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

  tryLoad()

  return {
    get () {
      return activeModule
    }
  }
}
