/**
 * Lightweight stub for /vendor/chart.umd.js used in Vitest jsdom tests.
 * The real file is a browser UMD bundle that sets window.Chart as a global.
 * Here we simply install a minimal Chart class on globalThis so that
 * chart-handler.mjs can construct it without errors.
 */
class Chart {
  constructor (ctx, config) {
    this.ctx = ctx
    this.data = (config && config.data) ? config.data : { datasets: [] }
    this.options = (config && config.options) ? config.options : {}
  }

  update () {}
  destroy () {}

  getElementsAtEventForMode () {
    return []
  }
}

globalThis.Chart = Chart

export {}
