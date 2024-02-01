/**
 * The purpose of this class is to store results as they occur and allow to
 * query for them, in addition to a specialized subscription focusing on results
 */
export class ResultManager {
  constructor (connectionManager, eventManager) {
    this.eventManager = eventManager
    this.eventManager.modelManager.subscribeSubResults((r) => {
      this.addResult(r)
    })
    this.results = {}
    this.subscribers = []
    this.results = {
      0: [],
      1: [],
      3: [],
      4: []
    }

    connectionManager.subscribe('subscription', (setToTrue) => {
      if (setToTrue) {
        this.activate()
      }
    })
  }

  addResult (result) {
    this.results[result.id] = result
    for (const subscriber of this.subscribers) {
      this.store(result)
      subscriber(result)
    }
  }

  activate () {
    this.eventManager.subscribeEvent(
      (model) => { // Filter
        return model.constructor.name === 'JoiningSystemResultReadyEventModel'
      },
      (model) => { // Callback
        this.addResult(model.Result)
      },
      'ResultManager subscription of the results'
    )
  }

  subscribe (func) {
    this.subscribers.push(func)
  }

  store (result) {
    let classification = 0
    if (result.classification) {
      classification = parseInt(result.classification)
    }
    this.results[classification].push(result)
    this.results[-1] = [result]
  }

  resultFromId (id, selectType) {
    for (const r of this.results[parseInt(selectType)]) {
      if (id === r.id) {
        return r
      }
    }
  }

  getLatest (resultType) {
    return this.results[resultType][this.results[resultType].length - 1]
  }

  getResultOfType (resultType) {
    return this.results[resultType]
  }
}
