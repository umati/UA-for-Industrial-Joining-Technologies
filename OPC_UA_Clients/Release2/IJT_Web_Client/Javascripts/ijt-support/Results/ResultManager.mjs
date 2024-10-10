/**
 * The purpose of this class is to store results as they occur and allow to
 * query for them, in addition to a specialized subscription focusing on results
 */
export class ResultManager {
  constructor (eventManager) {
    this.eventManager = eventManager
    this.eventManager.modelManager.subscribeSubResults((r) => {
      this.addResult(r)
    })
    this.results = {}
    this.subscribers = []
    this.resultUniqueCounter = 0
    this.unresolved = []
    this.results = {
      0: [],
      1: [],
      2: [],
      3: [],
      4: []
    }
  }

  /**
   * Go through all results containing uresolved references and check if
   * they can be resolved.
   * If they can, then remove them from the list of unresolveds.
   */
  resolveOld () {
    const cleanList = []
    for (const oldUnresolved of this.unresolved) {
      if (oldUnresolved.resolve(this)) {
        cleanList.push(oldUnresolved)
      }
    }
    this.unresolved.filter(item => !cleanList.includes(item))
  }

  handlePartial (stored, newResult) {
    if (newResult.ResultMetaData.SequenceNumber &&
      newResult.ResultMetaData.SequenceNumber >
      stored.ResultMetaData.SequenceNumber) {
      Object.assign(stored, newResult)
      return true
    }
    return false
  }

  /**
   * Store all new result for later use and let all subscribers know its here
   * @param {*} result the new result
   */
  addResult (result) {
    const stored = this.resultFromId(result.ResultMetaData.ResultId)

    if (stored) { // Old partial
      this.handlePartial(stored, result)
      this.unresolved.filter(item => item !== stored)
    } else { // New result
      let classification = 0
      if (result.classification) {
        classification = parseInt(result.classification)
      }
      result.uniqueCounter = this.resultUniqueCounter++
      this.results[classification].push(result)
      this.results[-1] = [result]
    }

    this.unresolved.push(result) // This result migh contain unresolved references
    this.resolveOld() // resolve all unresolved references that can be resolved

    result.clientLatestRecievedTime = new Date().getTime()

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
