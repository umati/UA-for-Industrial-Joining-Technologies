import { ModelManager } from '../Models/ModelManager.mjs'

export class ResultManager {
  constructor (connectionManager, eventManager) {
    this.eventManager = eventManager
    this.modelManager = new ModelManager()
    this.results = {}
    this.subscribers = []

    connectionManager.subscribe('subscription', (setToTrue) => {
      if (setToTrue) {
        this.activate()
      }
    })
  }

  addResult (result) {
    this.results[result.resultId] = result
    for (const subscriber of this.subscribers) {
      subscriber(result)
    }
  }

  activate () {
    this.eventManager.simpleSubscribeEvent(['Result'],
      (e) => { // Filter
        return e.Result?.value
      },
      (e) => { // Callback
        const model = this.modelManager.createModelFromRead(e.Result.value)
        this.addResult(model)
      },
      'ResultManager subscription of the results'
    )
  }

  subscribe (func) {
    this.subscribers.push(func)
  }
}
