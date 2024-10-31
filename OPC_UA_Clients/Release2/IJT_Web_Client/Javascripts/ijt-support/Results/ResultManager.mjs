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
    this.lastResult = null
  }

  getUnfinished () {
    const returnList = []
    for (const list of Object.values(this.results)) {
      for (const res of list) {
        if (!res.rebuildState.claimed ||
            (!res.rebuildState.claimed &&
              !res.rebuildState.partial &&
              res.rebuildState.resolved)) {
          returnList.push(res)
        }
      }
    }
    return returnList
  }

  /**
   * Go through all results containing uresolved references and check if
   * they can be resolved.
   * If they can, then remove them from the list of unresolveds.
   */
  resolveOld () {
    const cleanList = []
    for (const oldUnresolved of this.unresolved) {
      if (this.resolve(oldUnresolved)) {
        cleanList.push(oldUnresolved)
      }
    }

    // Something is wrong here since the partial job results are not cleaned
    // Or maybe it is just external results not counting???

    this.unresolved = this.unresolved.filter(item =>
      !cleanList.includes(item))
  }

  handlePartial (stored, newResult) {
    if (newResult.ResultMetaData.SequenceNumber &&
      newResult.ResultMetaData.SequenceNumber >
      stored.ResultMetaData.SequenceNumber) {
      const claimed = stored.rebuildState.claimed
      Object.assign(stored, newResult)
      stored.rebuildState.claimed = claimed
      return true
    }
    return false
  }

  /**
   * Store all new result for later use and let all subscribers know its here
   * @param {*} result the new result
   */
  addResult (result) {
    result.rebuildState.partial = result.ResultMetaData.IsPartial === 'True'
    const stored = this.resultFromId(result.ResultMetaData.ResultId)

    if (stored) { // Old partial
      this.handlePartial(stored, result)
      this.unresolved = this.unresolved.filter(item => item !== stored)
    } else { // New result
      let classification = 0
      if (result.classification) {
        classification = parseInt(result.classification)
      }
      result.uniqueCounter = this.resultUniqueCounter++
      this.results[classification].push(result)
      this.lastResult = result
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

  /**
   * This function resolves all references to child results
   * @param {*} result the result to resolve
   * @returns false if this result is not fully recieved (including all subresults)
   */
  resolve (result) {
    if (result.isReference) {
      const stored = this.resultFromId(result.ResultMetaData.ResultId)
      if (stored) {
        return stored
      } else {
        return false // Im not loaded yet
      }
    }

    // Go through all children and resolve them. If atleast one fails, I am still unresolved
    let returnValue = result
    result.rebuildState.resolved = true // Start by assuming all subresults are resolved
    if (result.ResultContent) {
      for (const child of result.ResultContent) {
        const newChild = this.resolve(child)
        if (!newChild) {
          returnValue = false // A child still lack a result
          result.rebuildState.resolved = false
        } else {
          newChild.rebuildState.claimed = true // This (sub)result could be purged now
          result.replaceReference(child, newChild, result.ResultContent)
        }
      }
    }
    return returnValue
  }
}
