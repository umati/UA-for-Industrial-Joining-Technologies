(function () {
  const runtime = window.__IJT_RUNTIME__ || {}
  const query = new URLSearchParams(window.location.search)

  function firstConfiguredValue (...values) {
    for (const value of values) {
      if (value !== undefined && value !== null && String(value).trim() !== '') {
        return String(value)
      }
    }
    return ''
  }

  function defaultHost () {
    return (window.location.hostname === 'localhost' ||
            window.location.hostname === '::1' ||
            window.location.hostname === '[::1]')
      ? '127.0.0.1'
      : window.location.hostname
  }

  window.APP_CONFIG = {
    get WS_HOST () {
      return firstConfiguredValue(query.get('wsHost'), runtime.WS_HOST, runtime.wsHost, defaultHost())
    },
    get WS_PORT () {
      return firstConfiguredValue(query.get('wsPort'), runtime.WS_PORT, runtime.wsPort)
    },
    get WS_PROTOCOL () {
      return firstConfiguredValue(
        query.get('wsProtocol'),
        runtime.WS_PROTOCOL,
        runtime.wsProtocol,
        window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      )
    },
    get ENVELOPE_LOOSENING_RESULT_HANDLING () {
      return firstConfiguredValue(
        query.get('envelopeLooseningResultHandling'),
        runtime.ENVELOPE_LOOSENING_RESULT_HANDLING,
        runtime.envelopeLooseningResultHandling,
        ''
      )
    },
    get ENVELOPE_ALIGN_ON_RUNDOWN_END () {
      return firstConfiguredValue(
        query.get('envelopeAlignOnRundownEnd'),
        runtime.ENVELOPE_ALIGN_ON_RUNDOWN_END,
        runtime.envelopeAlignOnRundownEnd,
        ''
      )
    },
    getWebSocketUrl: function () {
      const port = this.WS_PORT ? `:${this.WS_PORT}` : ''
      return `${this.WS_PROTOCOL}//${this.WS_HOST}${port}/`
    }
  }
})()
