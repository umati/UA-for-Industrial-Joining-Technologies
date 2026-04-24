import { ijtLog } from './ijt-logger.mjs'

/**
 * ObservableManagerBase - shared publish/subscribe behavior for manager classes.
 *
 * Topics are arbitrary string keys. Subclasses can expose domain-specific wrappers
 * (for example, `subscribe(state, cb)` or `subscribe(cb)`).
 */
export class ObservableManagerBase {
  constructor (debugName = 'ObservableManagerBase') {
    this.debugName = debugName
    this._topics = new Map()
  }

  _subscribeTopic (topic, callback) {
    if (typeof callback !== 'function') {
      return () => {}
    }
    const key = String(topic || 'default')
    if (!this._topics.has(key)) {
      this._topics.set(key, [])
    }
    const list = this._topics.get(key)
    list.push(callback)
    return () => {
      this._unsubscribeTopic(key, callback)
    }
  }

  _unsubscribeTopic (topic, callback) {
    const key = String(topic || 'default')
    const list = this._topics.get(key)
    if (!list || list.length === 0) {
      return
    }
    const index = list.indexOf(callback)
    if (index >= 0) {
      list.splice(index, 1)
    }
    if (list.length === 0) {
      this._topics.delete(key)
    }
  }

  _notifyTopic (topic, ...args) {
    const key = String(topic || 'default')
    const callbacks = this._topics.get(key)
    if (!callbacks || callbacks.length === 0) {
      return
    }
    for (const callback of [...callbacks]) {
      try {
        callback(...args)
      } catch (err) {
        ijtLog.error(`${this.debugName} callback for "${key}" threw:`, err)
      }
    }
  }
}
