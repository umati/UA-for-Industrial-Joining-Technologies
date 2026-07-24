/**
 * The purpose of this class is to store results as they occur and allow to
 * query for them, in addition to a specialized subscription focusing on results
 */
import { ijtLog } from '../ijt-logger.mjs'
import { ObservableManagerBase } from '../observable-manager-base.mjs'
import {
  createResultBundle,
  parseResultBundle,
  serializeResultForStorage
} from './result-serialization.mjs'
import {
  DEFAULT_IGNORE_LOOSENINGS,
  RESULT_SESSION_STORAGE_KEY
} from './result-storage-constants.mjs'
import ResultDataType from '../models/results/result-data-type.mjs'
import TighteningDataType from '../models/results/tightening-data-type.mjs'
import BatchDataModel from '../models/results/batch-data-type.mjs'
import JobDataModel from '../models/results/job-data-model.mjs'

const DEFAULT_MAX_STORED_RESULTS = 200
const MIN_MAX_STORED_RESULTS = 1
const RESULT_TOPIC_NEW = 'results'
const RESULT_TOPIC_EVICTED = 'results:evicted'

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

  normalizeBooleanSetting (value, fallback = false) {
    if (typeof value === 'boolean') {
      return value
    }
    if (typeof value === 'string') {
      const normalized = value.trim().toLowerCase()
      if (normalized === 'true') {
        return true
      }
      if (normalized === 'false') {
        return false
      }
    }
    return fallback
  }

  shouldIgnoreLooseningResults () {
    if (!this.settingsProvider) {
      return DEFAULT_IGNORE_LOOSENINGS
    }

    if (typeof this.settingsProvider.getIgnoreLoosenings === 'function') {
      return this.normalizeBooleanSetting(this.settingsProvider.getIgnoreLoosenings(), DEFAULT_IGNORE_LOOSENINGS)
    }

    const fromSettingsObject = this.settingsProvider?.settings?.ignoreloosenings
    if (fromSettingsObject !== undefined) {
      return this.normalizeBooleanSetting(fromSettingsObject, DEFAULT_IGNORE_LOOSENINGS)
    }

    return this.normalizeBooleanSetting(this.settingsProvider?.ignoreLoosenings, DEFAULT_IGNORE_LOOSENINGS)
  }

  shouldDropResult (result) {
    if (!this.shouldIgnoreLooseningResults()) {
      return false
    }

    if (typeof result?.isLoosening === 'function') {
      return result.isLoosening()
    }

    const assemblyType = result?.ResultMetaData?.AssemblyType
    return assemblyType === 2 || assemblyType === '2'
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

  getLatestFullResult () {
    const all = this.getAllResultsChronological()
    for (let index = all.length - 1; index >= 0; index--) {
      const candidate = all[index]
      if (!candidate || candidate.isReference) {
        continue
      }
      if (candidate.ResultMetaData?.IsPartial === 'True' || candidate.isPartial === true) {
        continue
      }
      return candidate
    }
    return null
  }

  getResultId (result) {
    return result?.ResultMetaData?.ResultId ?? result?.id ?? null
  }

  isResultReference (result) {
    if (!result || typeof result !== 'object') {
      return false
    }
    if (result.isReference === true) {
      return true
    }
    return !result?.ResultMetaData?.CreationTime && !!result?.ResultMetaData?.ResultId
  }

  collectResultClosure (rootResults = []) {
    const includedById = new Map()
    const stack = [...(Array.isArray(rootResults) ? rootResults : [rootResults])].filter(Boolean)
    const warnings = []

    while (stack.length > 0) {
      const current = stack.pop()
      const currentId = this.getResultId(current)
      if (!currentId || includedById.has(currentId)) {
        continue
      }
      includedById.set(currentId, current)

      const children = Array.isArray(current?.ResultContent) ? current.ResultContent : []
      for (const child of children) {
        if (!child) {
          continue
        }
        if (this.isResultReference(child)) {
          const refId = this.getResultId(child)
          const resolved = refId ? this.resultFromId(refId) : null
          if (resolved) {
            stack.push(resolved)
          } else {
            warnings.push({
              reason: 'missing_referenced_subresult',
              resultId: refId || null,
              parentId: currentId
            })
          }
        } else {
          stack.push(child)
        }
      }
    }

    return {
      results: [...includedById.values()],
      warnings
    }
  }

  exportBundle ({ rootResults = null, typeFilter = null, includeUnresolved = false } = {}) {
    let roots = []
    if (Array.isArray(rootResults) && rootResults.length > 0) {
      roots = rootResults.filter(Boolean)
    } else if (includeUnresolved) {
      roots = this.getUnfinished()
    } else if (Number.isFinite(typeFilter) && typeFilter >= 0) {
      roots = this.getResultOfType(typeFilter) || []
    } else {
      roots = this.getAllResultsChronological()
    }

    const closure = this.collectResultClosure(roots)
    const serializedRaw = closure.results
      .map((result) => serializeResultForStorage(result))
      .filter(Boolean)
    const exportedById = new Map()
    let duplicateExportIdsRemoved = 0

    for (const item of serializedRaw) {
      const resultId = item?.ResultMetaData?.ResultId
      if (!resultId) {
        continue
      }
      if (exportedById.has(resultId)) {
        duplicateExportIdsRemoved++
        continue
      }
      exportedById.set(resultId, item)
    }

    const serialized = [...exportedById.values()]

    if (duplicateExportIdsRemoved > 0) {
      closure.warnings.push({
        reason: 'duplicate_result_id_removed',
        count: duplicateExportIdsRemoved
      })
    }

    return {
      bundle: createResultBundle(serialized),
      warnings: closure.warnings,
      selectedRootCount: roots.length,
      exportedCount: serialized.length
    }
  }

  createRuntimeResultFromPayload (payload) {
    const modelManager = this.eventManager?.modelManager
    if (!modelManager) {
      return payload
    }
    try {
      const classification = Number.parseInt(payload?.ResultMetaData?.Classification, 10)
      switch (classification) {
        case 1:
          return new TighteningDataType(payload, modelManager)
        case 3:
          return new BatchDataModel(payload, modelManager)
        case 4:
          return new JobDataModel(payload, modelManager)
        default:
          return new ResultDataType(payload, modelManager)
      }
    } catch (error) {
      throw new Error(`Model conversion failed: ${error?.message || error}`)
    }
  }

  importBundleFromText (rawText, { mode = 'replace', strict = false } = {}) {
    const parsed = parseResultBundle(rawText)
    if (mode !== 'replace' && mode !== 'skip-duplicates') {
      throw new Error(`Invalid import mode '${mode}'`)
    }
    const summary = {
      total: parsed.results.length,
      imported: 0,
      skipped: 0,
      replaced: 0,
      skipReasons: {}
    }

    const incrementSkip = (reason) => {
      summary.skipped++
      summary.skipReasons[reason] = (summary.skipReasons[reason] || 0) + 1
    }

    for (const rawPayload of parsed.results) {
      const payload = serializeResultForStorage(rawPayload)
      if (!payload) {
        if (strict) {
          throw new Error('Import failed: invalid_result_shape')
        }
        incrementSkip('invalid_result_shape')
        continue
      }

      const resultId = payload?.ResultMetaData?.ResultId
      if (!resultId) {
        if (strict) {
          throw new Error('Import failed: missing_result_id')
        }
        incrementSkip('missing_result_id')
        continue
      }

      const alreadyStored = this.resultFromId(resultId)
      if (alreadyStored && mode === 'skip-duplicates') {
        incrementSkip('duplicate_result_id')
        continue
      }

      try {
        const runtimeResult = this.createRuntimeResultFromPayload(payload)
        const hadBefore = !!alreadyStored
        const storedResult = this.addResult(runtimeResult)
        if (!storedResult) {
          incrementSkip('ignored_loosening')
        } else if (hadBefore) {
          summary.replaced++
        } else {
          summary.imported++
        }
      } catch (error) {
        if (strict) {
          throw error
        }
        incrementSkip('invalid_result_shape')
      }
    }

    return summary
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

  /**
   * Clear all results from the manager and notify about the evictions
   */
  clear () {
    const allResults = this.getAllResultsChronological()
    for (const key of Object.keys(this.results)) {
      this.results[key] = []
    }
    this.unresolved = []
    this.lastResult = null
    for (const result of allResults) {
      this.notifyEvictedResult(result, 'user-clear')
    }
    // Clear persisted results from localStorage
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.removeItem(RESULT_SESSION_STORAGE_KEY)
    }
  }

  enforceStorageLimit () {
    const maxStoredResults = this.getMaxStoredResults()
    const chronological = this.getAllResultsChronological()
    const removeCount = chronological.length - maxStoredResults
    if (removeCount <= 0) {
      return
    }
    const removedCount = this.evictOldestResults(removeCount, 'storage-limit')
    if (removedCount > 0) {
      ijtLog.info(`Result storage capped at ${maxStoredResults}. Removed ${removedCount} oldest result(s).`)
    }
  }

  evictOldestResults (count = 1, reason = 'storage-limit') {
    const requested = Number.parseInt(count, 10)
    if (!Number.isFinite(requested) || requested <= 0) {
      return 0
    }
    const chronological = this.getAllResultsChronological()
    if (chronological.length === 0) {
      return 0
    }
    const toRemove = chronological.slice(0, Math.min(requested, chronological.length))
    for (const result of toRemove) {
      this.removeStoredResult(result)
      this.notifyEvictedResult(result, reason)
    }
    const refreshed = this.getAllResultsChronological()
    this.lastResult = refreshed.length > 0 ? refreshed[refreshed.length - 1] : null
    return toRemove.length
  }

  /**
   * Subscribe to results
   * @param {*} func the callback to call when new results occur
   */
  subscribe (func) {
    return this._subscribeTopic(RESULT_TOPIC_NEW, func)
  }

  /**
   * Subscribe to results that were removed by manager retention policies.
   * @param {*} func callback receiving eviction payload
   */
  subscribeEvicted (func) {
    return this._subscribeTopic(RESULT_TOPIC_EVICTED, func)
  }

  /**
   * Alias for subscribeEvicted.
   * @param {*} func callback receiving eviction payload
   */
  subscribeRemoved (func) {
    return this.subscribeEvicted(func)
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
    if (this.shouldDropResult(result)) {
      return false
    }
    if (!result?.ClientData) {
      result.ClientData = { rebuildState: { claimed: false, resolved: false, partial: false } }
    }
    if (!result.ClientData.rebuildState) {
      result.ClientData.rebuildState = { claimed: false, resolved: false, partial: false }
    }
    result.ClientData.rebuildState.partial = result?.ResultMetaData?.IsPartial === 'True'
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
    return true
  }

  notifyEvictedResult (result, reason = 'storage-limit') {
    if (!result) {
      return
    }
    this._notifyTopic(RESULT_TOPIC_EVICTED, {
      reason,
      resultId: this.getResultId(result),
      classification: result?.ResultMetaData?.Classification ?? result?.classification ?? null,
      uniqueCounter: Number.isFinite(result?.uniqueCounter) ? result.uniqueCounter : null,
      result
    })
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
