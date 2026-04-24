/**
 * The purpose of this class is to store results as they occur and allow to
 * query for them, in addition to a specialized subscription focusing on results
 */
import { ijtLog } from '../ijt-logger.mjs'
import { ObservableManagerBase } from '../observable-manager-base.mjs'

const DEFAULT_MAX_STORED_RESULTS = 200
const MIN_MAX_STORED_RESULTS = 1

export class ResultManager extends ObservableManagerBase {
  constructor (eventManager, settingsProvider = null) {
    super('ResultManager')
    this.eventManager = eventManager
    this.settingsProvider = settingsProvider
    this.eventManager.modelManager.subscribeSubResults((r) => {
      this.addResult(r)
    })
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

  getMaxStoredResults () {
    const fallback = DEFAULT_MAX_STORED_RESULTS
    const parseLimit = (value) => {
      const parsed = Number.parseInt(value, 10)
      if (!Number.isFinite(parsed) || parsed < MIN_MAX_STORED_RESULTS) {
        return null
      }
      return parsed
    }

    if (!this.settingsProvider) {
      return fallback
    }

    if (typeof this.settingsProvider.getMaxStoredResults === 'function') {
      const explicit = parseLimit(this.settingsProvider.getMaxStoredResults())
      if (explicit !== null) {
        return explicit
      }
    }

    const fromSettingsObject = parseLimit(this.settingsProvider?.settings?.maxstoredresults)
    if (fromSettingsObject !== null) {
      return fromSettingsObject
    }

    const fromDirectProp = parseLimit(this.settingsProvider?.maxStoredResults)
    if (fromDirectProp !== null) {
      return fromDirectProp
    }

    return fallback
  }

  getAllResultsChronological () {
    return Object
      .values(this.results)
      .flat()
      .sort((a, b) => {
        const left = Number.isFinite(a?.uniqueCounter) ? a.uniqueCounter : Number.MAX_SAFE_INTEGER
        const right = Number.isFinite(b?.uniqueCounter) ? b.uniqueCounter : Number.MAX_SAFE_INTEGER
        return left - right
      })
  }

  removeStoredResult (result) {
    if (!result) {
      return
    }
    for (const key of Object.keys(this.results)) {
      const list = this.results[key]
      const index = list.indexOf(result)
      if (index >= 0) {
        list.splice(index, 1)
      }
    }
    this.unresolved = this.unresolved.filter((item) => item !== result)
  }

  enforceStorageLimit () {
    const maxStoredResults = this.getMaxStoredResults()
    const chronological = this.getAllResultsChronological()
    const removeCount = chronological.length - maxStoredResults
    if (removeCount <= 0) {
      return
    }

    const toRemove = chronological.slice(0, removeCount)
    for (const result of toRemove) {
      this.removeStoredResult(result)
    }

    const refreshed = this.getAllResultsChronological()
    this.lastResult = refreshed.length > 0 ? refreshed[refreshed.length - 1] : null
    ijtLog.info(`Result storage capped at ${maxStoredResults}. Removed ${toRemove.length} oldest result(s).`)
  }

  /**
   * Subscribe to results
   * @param {*} func the callback to call when new results occur
   */
  subscribe (func) {
    return this._subscribeTopic('results', func)
  }

  /**
   * return a stored result
   * @param {*} id the id of the result that should be retrieved
   * @param {*} selectTypeInput use this result type if you want to narrow the serch (optional)
   * @returns a result
   */
  resultFromId (id, selectTypeInput) {
    const looplist = selectTypeInput ? [selectTypeInput] : Object.keys(this.results)
    for (const selectType of looplist) {
      const found = this.results[parseInt(selectType)].find((r) => id === r.id)
      if (found) return found
    }
  }

  /**
   * return the latest result of a given classification, or null if none stored.
   * @param {number} resultType the classification of the result you want
   * @returns {object|null} a result, or null if no results of that type exist
   */
  getLatest (resultType) {
    const list = this.results[resultType]
    if (!list || list.length === 0) return null
    return list[list.length - 1]
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
   * Store all new result for later use and let all subscribers know its here
   * @param {*} result the new result
   */
  addResult (result) {
    result.ClientData.rebuildState.partial = result.ResultMetaData.IsPartial === 'True'
    const stored = this.resultFromId(result.ResultMetaData.ResultId)

    if (stored) { // Old partial being extended
      this.handlePartial(stored, result)
      this.unresolved = this.unresolved.filter(item => item !== stored)
    } else { // New result
      let classification = 0
      if (result.classification) {
        classification = parseInt(result.classification)
      }
      result.uniqueCounter = this.resultUniqueCounter++ // Only needed in dropdown view. Remove it????
      this.results[classification].push(result)
      this.lastResult = result
    }

    this.unresolved.push(result) // This result migh contain unresolved references
    this.resolveOld() // resolve all unresolved references that can be resolved

    result.clientLatestRecievedTime = new Date().getTime()
    this.enforceStorageLimit()

    this._notifyTopic('results', result)
  }

  /**
   * This function resolves all references to child results
   * @param {*} result the result to resolve
   * @returns false if this result is not fully recieved (including all subresults)
   */
  resolve (result) {
    if (result.isReference) {
      return this.resultFromId(result.ResultMetaData.ResultId)
      /* if (stored) {
        return stored
      } else {
        return false // Im not loaded yet
      } */
    }

    // Go through all children and resolve them. If atleast one fails, I am still unresolved
    let returnValue = result
    result.ClientData.rebuildState.resolved = true // Start by assuming all subresults are resolved
    if (result.ResultContent) {
      for (const child of result.ResultContent) {
        const newChild = this.resolve(child)
        if (!newChild) {
          returnValue = false // A child still lack a result
          result.ClientData.rebuildState.resolved = false
        } else {
          newChild.ClientData.rebuildState.claimed = true // This (sub)result could be purged now
          result.replaceReference(child, newChild, result.ResultContent)
        }
      }
    }
    return returnValue
  }

  /**
   * this function returns a list of all complex results that contains
   * unresolved sub-results.
   * Unresolved means that it is a "partial" result, or a
   * job/batch where a subresult has not been recieved yet
   *
   * @returns {{}} a list of unresolved subresults
   */
  getUnfinished () {
    const returnList = []
    for (const list of Object.values(this.results)) {
      for (const res of list) {
        if (!res.ClientData.rebuildState.claimed ||
            (!res.ClientData.rebuildState.claimed &&
              !res.ClientData.rebuildState.partial &&
              res.ClientData.rebuildState.resolved)) {
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

    this.unresolved = this.unresolved.filter(item =>
      !cleanList.includes(item))
  }

  /**
   * Handles the merge of a new complex result extending an earlier
   * partial result
   * @param {*} stored A rartial result being recieved earlier
   * @param {*} newResult A new result (hopefully) with more data
   * @returns true if it was extended
   */
  handlePartial (stored, newResult) {
    if (newResult.ResultContent.length > stored.ResultContent.length ||
      newResult.ResultMetaData.IsPartial === 'False') {
      const claimed = stored.ClientData.rebuildState.claimed
      const safeResult = Object.fromEntries(
        Object.entries(newResult).filter(([k]) => !['__proto__', 'constructor', 'prototype'].includes(k))
      )
      Object.assign(stored, safeResult)
      stored.ClientData.rebuildState.claimed = claimed
      stored.ResultMetaData.IsPartial = newResult.ResultMetaData.IsPartial
      return true
    }
    return false
  }
}
