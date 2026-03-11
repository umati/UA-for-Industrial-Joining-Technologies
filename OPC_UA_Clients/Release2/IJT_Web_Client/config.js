window.APP_CONFIG = {
  WS_HOST: (window.location.hostname === 'localhost' || window.location.hostname === '::1')
    ? '127.0.0.1'
    : window.location.hostname,
  WS_PORT: '8001',
  WS_PROTOCOL: window.location.protocol === 'https:' ? 'wss:' : 'ws:',
  getWebSocketUrl: function () {
    return `${this.WS_PROTOCOL}//${this.WS_HOST}:${this.WS_PORT}/`
  }
}
