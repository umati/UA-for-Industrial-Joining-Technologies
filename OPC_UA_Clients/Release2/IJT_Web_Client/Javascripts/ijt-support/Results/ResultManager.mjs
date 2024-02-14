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
    this.resultUniqueCounter = 0
    this.results = {
      0: [],
      1: [],
      3: [],
      4: []
    }
  }

  /**
   * Store all new result for later use and
   * let all subscribers know its here
   * @param {*} result the new result
   */
  addResult (result) {
    this.results[result.id] = result
    result.clientLatestRecievedTime = new Date().getTime()

    let classification = 0
    if (result.classification) {
      classification = parseInt(result.classification)
    }
    result.uniqueCounter = this.resultUniqueCounter++
    this.results[classification].push(result)
    this.results[-1] = [result]

    for (const subscriber of this.subscribers) {
      subscriber(result)
    }
  }

  /**
   * Subscribe to results
   * @param {*} func the callback to call when new results occur
   */
  subscribe (func) {
    this.subscribers.push(func)
  }

  /**
   * return a stored result
   * @param {*} id the id of the result that should be retrieved
   * @param {*} selectTypeInput use this result type if you want to narrow the serch (optional)
   * @returns a result
   */
  resultFromId (id, selectTypeInput) {
    let looplist = [selectTypeInput]
    if (!selectTypeInput) {
      looplist = Object.keys(this.results)
    }
    for (const selectType of looplist) {
      for (const r of this.results[parseInt(selectType)]) {
        if (id === r.id) {
          return r
        }
      }
    }
  }

  /**
   * return the latest result of a given classification
   * @param {*} resultType the classification of the result you want
   * @returns a result
   */
  getLatest (resultType) {
    return this.results[resultType][this.results[resultType].length - 1]
  }

  /**
   * Get a list of all result of a given classification
   * @param {*} resultType the classification
   * @returns a list of all results with right classification
   */
  getResultOfType (resultType) {
    return this.results[resultType]
  }
}
