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
    this.results[result.id] = result
    for (const subscriber of this.subscribers) {
      subscriber(result)
    }
  }

  activate () {
    this.eventManager.subscribeEvent(
      (model) => { // Filter
        return model.constructor.name === 'JoiningSystemResultReadyEventModel'
      },
      (model) => { // Callback
        // const model = this.modelManager.createModelFromRead(e)
        this.addResult(model.Result)
      },
      'ResultManager subscription of the results'
    )
  }

  subscribe (func) {
    this.subscribers.push(func)
  }
}
