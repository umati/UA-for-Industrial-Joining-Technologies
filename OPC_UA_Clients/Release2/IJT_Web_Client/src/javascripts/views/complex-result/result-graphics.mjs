import BasicScreen from '../graphic-support/basic-screen.mjs'
import SimulateJobResultInvoker from '../graphic-support/simulate-job-result.mjs'
import { ijtLog } from '../../ijt-support/ijt-logger.mjs'
import {
  DEFAULT_RESULT_SESSION_AUTO_RESTORE,
  DEFAULT_RESULT_SESSION_AUTO_SAVE,
  RESULT_SESSION_STORAGE_KEY
} from '../../ijt-support/results/result-storage-constants.mjs'
/**
 * This illustrates how a nested result can be displayed
 */
const RESULT_SESSION_SAVE_DEBOUNCE_MS = 800
const STORAGE_QUOTA_ERROR_CODES = new Set([22, 1014])
const STORAGE_QUOTA_ERROR_NAMES = new Set(['QuotaExceededError', 'NS_ERROR_DOM_QUOTA_REACHED'])
const RESULT_SESSION_QUOTA_EVICT_BATCH_SIZE = 1

export default class ResultGraphics extends BasicScreen {
  constructor (resultManager, methodManager = null, addressSpace = null, eventManager = null, settingsProvider = null) {
    super('Consolidated Result')
    this.tabHelpText = 'Inspect aggregated results (tightening, batch, job) in hierarchical or enveloped view.'
    this.resultManager = resultManager
    this.simulateJobInvoker = (methodManager && addressSpace) ? new SimulateJobResultInvoker(methodManager, addressSpace) : null
    this.eventManager = eventManager
    this.settingsProvider = settingsProvider
    this.backGround.classList.add('consolidatedResultScreen')

    this.displayedIdentity = 0
    this.selectType = '-1'
    this.selectResult = '-2'
    this.envelope = 'false'
    this.toggleQueueingState = false
    this.hoverDiv = null
    this.queueInfo = null
    this.importMode = 'replace'
    this.importStrict = false
    this.selectedExportResultIds = new Set()
    this._sessionSaveTimer = null
    this._busyCounter = 0
    this.ensureStatusBanner('results')
    this.setStatusBanner('results', 'empty', 'No results yet.')
    // Subscribe to new results
    resultManager.subscribe((result) => {
      this.refreshDrawing(result.id)
      this.setStatusBanner('results', 'success', `Updated result: ${result.id}`)
      this.scheduleSessionPersist()
    })
    this.attachEvictedResultsSubscription()

    this.header = document.createElement('div')
    this.header.classList.add('resultHeader', 'resultheader')
    this.backGround.appendChild(this.header)

    this.headerLeft = document.createElement('div')
    this.headerLeft.classList.add('resultHeaderLeft')
    this.header.appendChild(this.headerLeft)

    this.headerCenter = document.createElement('div')
    this.headerCenter.classList.add('resultHeaderCenter')
    this.header.appendChild(this.headerCenter)

    this.headerRight = document.createElement('div')
    this.headerRight.classList.add('resultHeaderRight')
    this.header.appendChild(this.headerRight)

    this.simulateJobButton = this.createButton('Simulate', this.headerCenter, async () => {
      await this.simulateJobResult()
    })
    this.simulateJobButton.classList.remove('resultHeaderItem')
    this.simulateJobButton.classList.add('demoButton', 'resultHeaderRightAction')
    this.simulateJobButton.title = 'Trigger a simulated Job result from the server.'
    if (!this.simulateJobInvoker) {
      this.simulateJobButton.disabled = true
      this.simulateJobButton.title = 'Job simulation method setup unavailable in this context.'
    }

    this.toggleQueueingButton = this.createButton('Queue', this.headerCenter, () => {
      this.toggleQueueingState = !this.toggleQueueingState
      this.eventManager.queueState(this.toggleQueueingState)
      this.hoveringStepButton(this.toggleQueueingState)
    })
    this.toggleQueueingButton.classList.remove('resultHeaderItem')
    this.toggleQueueingButton.classList.add('demoButton', 'resultHeaderRightAction')
    this.toggleQueueingButton.title = 'Toggle event queue mode. When enabled, events can be stepped manually.'
    if (!this.eventManager || typeof this.eventManager.queueState !== 'function') {
      this.toggleQueueingButton.disabled = true
      this.toggleQueueingButton.title = 'Event manager unavailable in this context.'
    }

    this.exportResultsButton = this.createButton('Export', this.headerRight, () => {
      this.exportSelectedResults()
    })
    this.exportResultsButton.classList.remove('resultHeaderItem')
    this.exportResultsButton.classList.add('demoButton', 'resultHeaderRightAction')
    this.exportResultsButton.title = 'Export selected result boxes. If none are selected, exports the latest visible box with full hierarchy.'

    this.importResultsButton = this.createButton('Import', this.headerRight, () => {
      this.importFileInput.click()
    })
    this.importResultsButton.classList.remove('resultHeaderItem')
    this.importResultsButton.classList.add('demoButton', 'resultHeaderRightAction')
    this.importResultsButton.title = 'Import result bundle JSON file into the current result manager.'

    this.importModeDropdown = this.createDropdown('Import mode', (selection) => {
      this.importMode = selection === 'skip-duplicates' ? 'skip-duplicates' : 'replace'
    })
    this.importModeDropdown.addOption('Replace', 'replace')
    this.importModeDropdown.addOption('Skip duplicates', 'skip-duplicates')
    this.importModeDropdown.select.value = this.importMode
    this.importModeDropdown.classList.add('resultHeaderItem', 'resultImportMode')
    this.importModeDropdown.title = 'Import mode controls duplicate ResultId handling.'
    this.importModeDropdown.select.title = 'Replace: incoming results with existing IDs overwrite stored ones. Skip duplicates: existing IDs are kept.'
    this.headerRight.appendChild(this.importModeDropdown)

    this.importStrictLabel = document.createElement('label')
    this.importStrictLabel.classList.add('resultImportStrict')
    this.importStrictLabel.title = 'Strict import fails the entire import on first invalid result.'
    const strictText = document.createElement('span')
    strictText.textContent = 'Strict'
    this.importStrictLabel.appendChild(strictText)
    this.importStrictCheckbox = this.createCheckbox(this.importStrict, (checked) => {
      this.importStrict = !!checked
    })
    this.importStrictCheckbox.classList.add('resultImportStrictInput')
    this.importStrictCheckbox.title = 'Strict import fails the full import when one result is invalid.'
    this.importStrictLabel.appendChild(this.importStrictCheckbox)
    this.headerRight.appendChild(this.importStrictLabel)

    this.importFileInput = document.createElement('input')
    this.importFileInput.type = 'file'
    this.importFileInput.accept = '.json,application/json'
    this.importFileInput.classList.add('resultImportInput')
    this.importFileInput.addEventListener('change', async () => {
      await this.importSelectedFile()
    })
    this.headerRight.appendChild(this.importFileInput)

    // Type selection dropdown
    this.selectResultType = this.createDropdown('Type', (selection) => {
      this.selectType = parseInt(selection)
      this.changeResultList(selection)
      this.refreshDrawing(this.selectResult)
    })
    this.selectResultType.addOption('Latest', -1)
    this.selectResultType.addOption('Jobs', 4)
    this.selectResultType.addOption('Batches', 3)
    this.selectResultType.addOption('Single tightenings', 1)
    this.selectResultType.addOption('Other', 0)
    this.selectResultType.classList.add('resultHeaderItem')
    this.selectResultType.title = 'Filter results by classification.'
    this.selectResultType.select.title = 'Choose which result type to list.'
    // E2E selectors consume these stable control hooks; keep them with the rendered controls.
    this.selectResultType.select.setAttribute('data-ijt-result-control', 'type')
    this.headerLeft.appendChild(this.selectResultType)

    // Result selection dropdown
    this.selectResultDropdown = this.createDropdown('Result', (selection) => {
      this.selectResult = selection
      this.refreshDrawing(selection)
    })
    this.selectResultDropdown.addOption('Unresolved', -2)
    this.selectResultDropdown.addOption('Latest', -1)
    this.selectResultDropdown.classList.add('resultHeaderItem')
    this.selectResultDropdown.title = 'Choose which result root to render.'
    this.selectResultDropdown.select.title = 'Select unresolved, latest, or a specific result.'
    this.selectResultDropdown.select.setAttribute('data-ijt-result-control', 'result')
    this.headerLeft.appendChild(this.selectResultDropdown)

    // display type dummy selection dropdown
    this.dummyDropdown = this.createDropdown('View', (selection) => {
      this.envelope = selection
      this.refreshDrawing(this.selectResult)
    })

    this.dummyDropdown.addOption('Hierarchical', false)
    this.dummyDropdown.addOption('Enveloped', true)
    this.dummyDropdown.classList.add('resultHeaderItem')
    this.dummyDropdown.title = 'Change how nested result hierarchy is displayed.'
    this.dummyDropdown.select.title = 'Hierarchical shows tree branches. Enveloped shows full-width nested boxes.'
    this.dummyDropdown.select.setAttribute('data-ijt-result-control', 'view')
    this.headerLeft.appendChild(this.dummyDropdown)

    this.display = document.createElement('div')
    this.display.classList.add('drawResultBox')
    this.backGround.appendChild(this.display)

    this._narrowLabelRafId = 0
    this._narrowLabelResizeHandler = () => {
      this.scheduleNarrowLabelVisibility()
    }
    window.addEventListener('resize', this._narrowLabelResizeHandler)
    if (typeof window.ResizeObserver === 'function') {
      this._narrowLabelObserver = new window.ResizeObserver(() => {
        this.scheduleNarrowLabelVisibility()
      })
      this._narrowLabelObserver.observe(this.display)
      this._narrowLabelObserver.observe(this.backGround)
    }

    this.restoreSessionFromLocalStorage()
  }

  getVisibleRootResults () {
    if (this.selectResult === '-2') {
      return this.resultManager.getUnfinished()
    }
    if (this.selectType === -1) {
      return [this.resultManager.lastResult].filter(Boolean)
    }
    if (this.selectResult === '-1') {
      return [this.resultManager.getLatest(this.selectType)].filter(Boolean)
    }
    return [this.resultManager.resultFromId(this.selectResult, this.selectType)].filter(Boolean)
  }

  getExportRootResults () {
    const selected = [...this.selectedExportResultIds]
      .map((id) => this.resultManager.resultFromId(id))
      .filter(Boolean)
    if (selected.length > 0) {
      return { roots: selected, mode: 'selection' }
    }
    const visibleRoots = this.getVisibleRootResults()
    if (visibleRoots.length > 0) {
      return { roots: [visibleRoots[visibleRoots.length - 1]], mode: 'fallback-latest-visible-box' }
    }
    const latestFull = this.resultManager.getLatestFullResult()
    if (latestFull) {
      return { roots: [latestFull], mode: 'fallback-latest-full-global' }
    }
    if (this.resultManager.lastResult) {
      return { roots: [this.resultManager.lastResult], mode: 'fallback-latest-any-global' }
    }
    return { roots: [], mode: 'none' }
  }

  createExportSelectionControl (wrapper, result) {
    const resultId = result?.id
    if (!resultId) {
      return
    }

    const label = document.createElement('label')
    label.classList.add('resultExportSelect')
    label.title = `Include ${resultId} in export`

    const input = document.createElement('input')
    input.type = 'checkbox'
    input.classList.add('resultExportSelectInput')
    input.setAttribute('aria-label', `Include result ${resultId} in export`)
    input.checked = this.selectedExportResultIds.has(resultId)
    input.addEventListener('change', () => {
      if (input.checked) {
        this.selectedExportResultIds.add(resultId)
      } else {
        this.selectedExportResultIds.delete(resultId)
      }
    })
    label.appendChild(input)

    const text = document.createElement('span')
    text.classList.add('resultExportSelectText')
    text.textContent = 'Include in export'
    label.appendChild(text)

    wrapper.appendChild(label)
  }

  makeExportFileName () {
    const stamp = new Date().toISOString().replace(/[:.]/g, '-')
    return `ijt-results-${stamp}.json`
  }

  downloadTextFile (text, filename) {
    const blob = new Blob([text], { type: 'application/json;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    window.URL.revokeObjectURL(url)
  }

  exportSelectedResults () {
    this.beginBusyState('Preparing export...')
    try {
      const { roots, mode } = this.getExportRootResults()
      if (roots.length === 0) {
        this.setStatusBanner('results', 'empty', 'No result available to export.')
        return
      }
      const exported = this.resultManager.exportBundle({ rootResults: roots })
      const text = JSON.stringify(exported.bundle)
      this.downloadTextFile(text, this.makeExportFileName())
      const warningCount = exported.warnings?.length || 0
      const warningSuffix = warningCount > 0 ? ` (${warningCount} missing sub-results)` : ''
      this.setStatusBanner('results', 'success', `Exported ${exported.exportedCount} result(s) via ${mode}${warningSuffix}.`)
    } catch (error) {
      this.setStatusBanner('results', 'error', `Export failed: ${error?.message || error}`)
    } finally {
      this.endBusyState()
    }
  }

  async importSelectedFile () {
    const file = this.importFileInput?.files?.[0]
    if (!file) {
      return
    }
    this.beginBusyState('Importing results...')
    try {
      const text = await file.text()
      const summary = this.resultManager.importBundleFromText(text, { mode: this.importMode, strict: this.importStrict })
      let message = `Imported ${summary.imported}, replaced ${summary.replaced}, skipped ${summary.skipped} of ${summary.total}.`
      if (summary.skipped > 0) {
        const reasons = Object.entries(summary.skipReasons || {}).map(([reason, count]) => `${reason}:${count}`).join(', ')
        message += ` Reasons: ${reasons}`
      }
      this.setStatusBanner('results', summary.skipped > 0 ? 'info' : 'success', message)
      this.refreshDrawing(this.selectResult)
      this.scheduleSessionPersist()
    } catch (error) {
      this.setStatusBanner('results', 'error', `Import failed: ${error?.message || error}`)
    } finally {
      this.importFileInput.value = ''
      this.endBusyState()
    }
  }

  beginBusyState (message = 'Working...') {
    this._busyCounter = Math.max(0, this._busyCounter) + 1
    this.backGround.classList.add('isResultBusy')
    this.setStatusBanner('results', 'loading', message)
    this.setHeaderInteractivity(false)
  }

  endBusyState () {
    this._busyCounter = Math.max(0, this._busyCounter - 1)
    if (this._busyCounter > 0) {
      return
    }
    this.backGround.classList.remove('isResultBusy')
    this.setHeaderInteractivity(true)
  }

  setHeaderInteractivity (enabled) {
    const controls = [
      this.simulateJobButton,
      this.toggleQueueingButton,
      this.exportResultsButton,
      this.importResultsButton,
      this.importModeDropdown?.select,
      this.importStrictCheckbox,
      this.selectResultType?.select,
      this.selectResultDropdown?.select,
      this.dummyDropdown?.select
    ].filter(Boolean)

    for (const control of controls) {
      control.disabled = !enabled
    }
  }

  canUseLocalStorage () {
    try {
      return typeof window !== 'undefined' && !!window.localStorage
    } catch (_error) {
      return false
    }
  }

  isStorageQuotaExceededError (error) {
    if (!error) {
      return false
    }
    const name = typeof error.name === 'string' ? error.name : ''
    if (STORAGE_QUOTA_ERROR_NAMES.has(name)) {
      return true
    }
    if (STORAGE_QUOTA_ERROR_CODES.has(Number(error.code))) {
      return true
    }
    const message = typeof error.message === 'string' ? error.message : ''
    return /quota/i.test(message)
  }

  scheduleSessionPersist () {
    if (!this.isSessionAutoSaveEnabled()) {
      return
    }
    if (!this.canUseLocalStorage()) {
      return
    }
    if (this._sessionSaveTimer) {
      window.clearTimeout(this._sessionSaveTimer)
      this._sessionSaveTimer = null
    }
    this._sessionSaveTimer = window.setTimeout(() => {
      this._sessionSaveTimer = null
      this.persistSessionToLocalStorage()
    }, RESULT_SESSION_SAVE_DEBOUNCE_MS)
  }

  persistSessionToLocalStorage () {
    if (!this.canUseLocalStorage()) {
      return
    }
    const maxAttempts = Math.max(1, this.resultManager?.getAllResultsChronological?.()?.length || 1)
    let discardedCount = 0
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const exported = this.resultManager.exportBundle()
        if (exported.exportedCount <= 0) {
          window.localStorage.removeItem(RESULT_SESSION_STORAGE_KEY)
          if (discardedCount > 0) {
            this.refreshDrawing(this.selectResult)
            this.setStatusBanner('results', 'info', `Local session storage was full. Discarded ${discardedCount} oldest trace${discardedCount === 1 ? '' : 's'} to keep autosave running.`)
          }
          return
        }
        const text = JSON.stringify(exported.bundle)
        window.localStorage.setItem(RESULT_SESSION_STORAGE_KEY, text)
        if (discardedCount > 0) {
          this.refreshDrawing(this.selectResult)
          this.setStatusBanner('results', 'info', `Local session storage was full. Discarded ${discardedCount} oldest trace${discardedCount === 1 ? '' : 's'} to keep autosave running.`)
        }
        return
      } catch (error) {
        if (!this.isStorageQuotaExceededError(error)) {
          ijtLog.warn('Result session persistence failed:', error?.message || error)
          return
        }
        const evictedCount = this.resultManager?.evictOldestResults?.(RESULT_SESSION_QUOTA_EVICT_BATCH_SIZE, 'session-storage-quota') || 0
        if (evictedCount <= 0) {
          ijtLog.warn('Result session persistence failed: local session storage quota exceeded and no older traces could be discarded.')
          this.setStatusBanner('results', 'error', 'Local session storage is full. Autosave could not free space.')
          return
        }
        discardedCount += evictedCount
      }
    }
    ijtLog.warn('Result session persistence failed: local session storage quota recovery reached retry limit.')
  }

  restoreSessionFromLocalStorage () {
    if (!this.isSessionAutoRestoreEnabled()) {
      return
    }
    if (!this.canUseLocalStorage()) {
      return
    }
    const existingCount = this.resultManager.getAllResultsChronological().length
    if (existingCount > 0) {
      return
    }
    const raw = window.localStorage.getItem(RESULT_SESSION_STORAGE_KEY)
    if (!raw) {
      return
    }
    try {
      const summary = this.resultManager.importBundleFromText(raw, { mode: 'replace', strict: false })
      if (summary.total <= 0) {
        this.setStatusBanner('results', 'empty', 'No restorable results found in local session.')
        return
      }
      let message = `Restored ${summary.imported}, replaced ${summary.replaced}, skipped ${summary.skipped} of ${summary.total} from local session.`
      if (summary.skipped > 0) {
        const reasons = Object.entries(summary.skipReasons || {}).map(([reason, count]) => `${reason}:${count}`).join(', ')
        message += ` Reasons: ${reasons}`
      }
      this.setStatusBanner('results', summary.skipped > 0 ? 'info' : 'success', message)
      this.refreshDrawing(this.selectResult)
    } catch (error) {
      ijtLog.warn('Result session restore failed:', error?.message || error)
      this.setStatusBanner('results', 'error', 'Stored local results are invalid and were ignored.')
    }
  }

  normalizeBooleanSetting (value, fallback = true) {
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

  isSessionAutoSaveEnabled () {
    if (!this.settingsProvider) {
      return DEFAULT_RESULT_SESSION_AUTO_SAVE
    }
    if (typeof this.settingsProvider.getResultSessionAutoSave === 'function') {
      return this.normalizeBooleanSetting(this.settingsProvider.getResultSessionAutoSave(), DEFAULT_RESULT_SESSION_AUTO_SAVE)
    }
    return this.normalizeBooleanSetting(this.settingsProvider?.settings?.resultsessionautosave, DEFAULT_RESULT_SESSION_AUTO_SAVE)
  }

  isSessionAutoRestoreEnabled () {
    if (!this.settingsProvider) {
      return DEFAULT_RESULT_SESSION_AUTO_RESTORE
    }
    if (typeof this.settingsProvider.getResultSessionAutoRestore === 'function') {
      return this.normalizeBooleanSetting(this.settingsProvider.getResultSessionAutoRestore(), DEFAULT_RESULT_SESSION_AUTO_RESTORE)
    }
    return this.normalizeBooleanSetting(this.settingsProvider?.settings?.resultsessionautorestore, DEFAULT_RESULT_SESSION_AUTO_RESTORE)
  }

  attachEvictedResultsSubscription () {
    const subscribeEvicted = this.resultManager?.subscribeEvicted
    const subscribeRemoved = this.resultManager?.subscribeRemoved
    const subscribeFn = typeof subscribeEvicted === 'function'
      ? subscribeEvicted.bind(this.resultManager)
      : (typeof subscribeRemoved === 'function' ? subscribeRemoved.bind(this.resultManager) : null)
    if (!subscribeFn) {
      return
    }
    subscribeFn((evt) => {
      this.handleEvictedResult(evt)
    })
  }

  resolveResultIdFromEvent (evt) {
    const fromPayload = evt?.resultId
    if (typeof fromPayload === 'string' || typeof fromPayload === 'number') {
      return String(fromPayload)
    }
    const fromResult = evt?.result?.id ?? evt?.result?.ResultMetaData?.ResultId
    if (typeof fromResult === 'string' || typeof fromResult === 'number') {
      return String(fromResult)
    }
    if (typeof evt === 'string' || typeof evt === 'number') {
      return String(evt)
    }
    return null
  }

  handleEvictedResult (evt) {
    const resultId = this.resolveResultIdFromEvent(evt)
    if (!resultId) {
      return
    }
    const nextSelected = new Set()
    for (const id of this.selectedExportResultIds) {
      if (String(id) === resultId) {
        continue
      }
      nextSelected.add(id)
    }
    this.selectedExportResultIds = nextSelected
  }

  activate () {
    if (!this.simulateJobInvoker) {
      return
    }
    this.simulateJobInvoker.prepare().catch(() => {})
  }

  async simulateJobResult () {
    if (!this.simulateJobInvoker) {
      return
    }
    this.setStatusBanner('results', 'loading', 'Running result simulation...')
    try {
      await this.simulateJobInvoker.invoke()
      this.setStatusBanner('results', 'success', 'Simulation request sent.')
    } catch (error) {
      this.setStatusBanner('results', 'error', `Simulation failed: ${error?.message || error}`)
      this.messageDisplay(`Job simulation failed: ${error?.message || error}`)
    }
  }

  hoveringStepButton (_toggleQueueingState) {
    if (!this.eventManager?.queue) {
      return
    }

    const nameValueElement = (name, value) => {
      const resultDiv = document.createElement('div')
      resultDiv.classList.add('eventQueuePeeks')
      const nameDiv = document.createElement('div')
      resultDiv.appendChild(nameDiv)
      const valDiv = document.createElement('div')
      resultDiv.appendChild(valDiv)
      nameDiv.innerText = name
      if (value) {
        if (value.Message) {
          valDiv.innerText = value.Message.Text
        } else {
          valDiv.innerText = value
        }
      }
      return resultDiv
    }

    const queue = this.eventManager.queue
    if (!this.hoverDiv) {
      this.hoverDiv = document.createElement('div')
      this.hoverDiv.classList.add('eventqueuehoverdiv')
      document.body.appendChild(this.hoverDiv)

      this.hoverDiv.innerText = 'Event queue'

      this.createButton('Next event', this.hoverDiv, () => {
        this.queueInfo.innerHTML = ''
        this.queueInfo.appendChild(nameValueElement('Last', this.eventManager.dequeue()))
        this.queueInfo.appendChild(nameValueElement('Next', queue.peek()))
        this.queueInfo.appendChild(nameValueElement('Size', this.eventManager.queue.size()))
      })

      this.createButton('Scramble', this.hoverDiv, () => {
        const array = this.eventManager.queue
        let currentIndex = array.length

        while (currentIndex !== 0) {
          const randomIndex = Math.floor(Math.random() * currentIndex)
          currentIndex--
          ;[array[currentIndex], array[randomIndex]] = [array[randomIndex], array[currentIndex]]
        }
      })

      this.queueInfo = document.createElement('div')
      this.queueInfo.classList.add('eventInfo')
      this.hoverDiv.appendChild(this.queueInfo)
    } else {
      document.body.removeChild(this.hoverDiv)
      this.hoverDiv = null
      this.queueInfo = null
    }
  }

  /**
   * Support function that applies a list of styles to an element
   * @date 2/12/2024 - 7:27:41 PM
   *
   * @param {*} element
   * @param {*} list
   */
  applyClasses (element, list) {
    for (const style of list) {
      element.classList.add(style)
    }
  }

  /**
   * Centralized label text setter so newline behavior is consistent.
   * @param {HTMLElement} element
   * @param {string} text
   */
  setLabelText (element, text) {
    if (!element) {
      return
    }
    const value = (typeof text === 'string') ? text : ''
    element.textContent = value
    element.style.whiteSpace = value.includes('\n') ? 'pre-line' : ''
  }

  /**
   * If label ends with "Result: <number>" (optionally followed by "[x/y]"),
   * force a line break before that result suffix.
   * @param {string} text
   * @returns {string}
   */
  wrapBeforeResultText (text) {
    if (typeof text !== 'string') {
      return text
    }
    const trimmed = text.trim()
    const match = trimmed.match(/^(.*?)(Result\s*:\s*[+-]?\d+(?:[.,]\d+)?(?:\s*\[[^\]]+\])?)$/i)
    if (!match) {
      return trimmed
    }
    const before = match[1].trimEnd()
    if (!before) {
      return trimmed
    }
    const suffix = match[2].trim()
    return `${before}\n${suffix}`
  }

  getResultBoxLabelText (result) {
    const name = typeof result?.name === 'string' ? result.name.trim() : ''
    const evaluationDetails = typeof result?.ResultMetaData?.ResultEvaluationDetails?.Text === 'string'
      ? result.ResultMetaData.ResultEvaluationDetails.Text.trim()
      : ''

    if (name && evaluationDetails && name !== evaluationDetails) {
      return `${evaluationDetails}\n${name}`
    }
    if (evaluationDetails) {
      return evaluationDetails
    }
    if (name) {
      return name
    }
    return ''
  }

  /**
   * Hide label text when the rendered box width is too narrow to reasonably
   * fit 10 letters, to avoid very tall wrapped boxes.
   * @param {HTMLElement} scope
   */
  applyNarrowLabelVisibility (scope) {
    if (!scope) {
      return
    }
    const labels = scope.querySelectorAll('.resultBoxLabel')
    for (const label of labels) {
      const fullText = label._fullText || label.textContent || ''
      label._fullText = fullText
      if (!fullText) {
        continue
      }
      if (this.isTooNarrowForLettersWithText(label, fullText, 10)) {
        this.setLabelText(label, this.getCollapsedLabelText(fullText))
        label.title = fullText
      } else if (label.textContent !== fullText) {
        this.setLabelText(label, fullText)
        label.title = ''
      } else {
        // Re-assert white-space in case styles were reset externally.
        label.style.whiteSpace = fullText.includes('\n') ? 'pre-line' : ''
      }
    }
  }

  /**
   * @param {string} text
   * @returns {string}
   */
  getCollapsedLabelText (text) {
    if (typeof text !== 'string' || text.length === 0) {
      return ''
    }
    const trimmed = text.trim()
    return trimmed.length > 0 ? trimmed[0] : ''
  }

  /**
   * Measure narrowness using the full label text regardless of current hidden/visible state.
   * This allows hidden labels to re-appear once room is available.
   * @param {HTMLElement} element
   * @param {string} text
   * @param {number} letterCount
   * @returns {boolean}
   */
  isTooNarrowForLettersWithText (element, text, letterCount) {
    if (!element) {
      return false
    }
    const previousText = element.textContent
    const previousWhiteSpace = element.style.whiteSpace
    this.setLabelText(element, text)
    const result = this.isTooNarrowForLetters(element, letterCount)
    this.setLabelText(element, previousText || '')
    element.style.whiteSpace = previousWhiteSpace
    return result
  }

  /**
   * @param {HTMLElement} element
   * @param {number} letterCount
   * @returns {boolean}
   */
  isTooNarrowForLetters (element, letterCount) {
    if (!element || !letterCount) {
      return false
    }
    const width = element.getBoundingClientRect().width
    if (!width || width <= 0) {
      return false
    }
    const computed = window.getComputedStyle(element)
    const font = computed.font || `${computed.fontStyle} ${computed.fontVariant} ${computed.fontWeight} ${computed.fontSize}/${computed.lineHeight} ${computed.fontFamily}`
    const canvas = this._textMeasureCanvas || document.createElement('canvas')
    this._textMeasureCanvas = canvas
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      return false
    }
    ctx.font = font
    const sample = 'aaaaaaaaaa'.substring(0, Math.max(1, letterCount))
    const neededWidth = ctx.measureText(sample).width
    return width < neededWidth
  }

  scheduleNarrowLabelVisibility () {
    if (this._narrowLabelRafId) {
      window.cancelAnimationFrame(this._narrowLabelRafId)
      this._narrowLabelRafId = 0
    }
    this._narrowLabelRafId = window.requestAnimationFrame(() => {
      this._narrowLabelRafId = 0
      this.applyNarrowLabelVisibility(this.display)
      window.requestAnimationFrame(() => {
        this.applyNarrowLabelVisibility(this.display)
      })
    })
  }

  /**
   * This function returns a HTML representation of the parent and its children
   * @date 2/12/2024 - 7:24:26 PM
   *
   * @param {*} parentBox the top result
   * @param {*} children a list of children
   * @param {*} counter the current counter of for example a batch
   * @param {*} size the size of for example a batch
   * @param {*} state the state of the result (in progress, completed, aborted, ...)
   * @param {*} enveloped should it be represented as enveloped boxes or hierarchical roots
   * @returns {*} a HTML representation of the parent-child relation
   */
  makeRoot (parentBox, children, counter, size, enveloped) {
    const makeSnibb = (container, counter, length) => {
      const row = document.createElement('div')
      row.classList.add('snibbRow')
      container.appendChild(row)
      const left = document.createElement('div')
      left.classList.add('snibbNone')
      row.appendChild(left)
      const right = document.createElement('div')
      if (enveloped) {
        right.classList.add('snibbNone')
      } else {
        right.classList.add('snibbRight')
      }
      if ((!enveloped) && (counter !== 0)) {
        left.classList.add('snibbTopRef')
      }
      if ((!enveloped) && (length - counter > 1)) {
        right.classList.add('snibbTopRef')
      }
      row.appendChild(right)
    }

    const container = document.createElement('div')
    const top = document.createElement('div')
    top.classList.add('rootTop')
    container.appendChild(top)

    const parentCenter = document.createElement('div')
    if (enveloped) {
      parentCenter.classList.add('rootCenterHier')
    } else {
      parentCenter.classList.add('rootCenterRef')
    }
    top.appendChild(parentCenter)
    parentCenter.appendChild(parentBox)

    if (children.length === 0) { // Skip rest if no children
      return container
    }

    if (!enveloped) {
      makeSnibb(parentCenter, 0, 0)
    }

    const bottom = document.createElement('div')
    bottom.classList.add('horStack')
    container.appendChild(bottom)

    for (let i = 0; i < children.length; i++) {
      const child = children[i].element
      const style = children[i].style
      const childContainer = document.createElement('div')
      if (enveloped) {
        childContainer.classList.add('rootChildHier')
      } else {
        childContainer.classList.add('rootChildRef')
      }
      bottom.appendChild(childContainer)

      if (!enveloped) {
        makeSnibb(childContainer, i, children.length)
      }
      childContainer.appendChild(child)

      if (enveloped) {
        this.applyClasses(childContainer, style)
      }
    }
    return container
  }

  /**
   * update the dropdown of results
   * @param {*} selectedtype the classification of results that should be in the dropdown
   */
  changeResultList (selectedtype) {
    this.selectResultDropdown.clearOptions()
    this.selectResultDropdown.addOption('Unresolved', -2)
    this.selectResultDropdown.addOption('Latest', -1)
    for (const a of this.resultManager.getResultOfType(parseInt(selectedtype))) {
      this.selectResultDropdown.addOption(`${a.name} [${a.time.substring(11, 19)}] ${a.uniqueCounter}`, a.id)
    }
  }

  /**
   * Draw nested boxes that respresents a complex result
   * @date 2/2/2024 - 8:38:34 AM
   *
   * @param {*} id the identity of what you want to draw
   */
  refreshDrawing (id) {
    this.display.innerHTML = ''
    this.display.classList.toggle('drawResultBoxEnveloped', this.envelope === 'true')
    const selection = this.getVisibleRootResults()
    let renderedCount = 0
    for (const result of selection) {
      const drawResult = this.drawResultBoxes(result)
      if (drawResult) {
        if (this.envelope === 'true') {
          this.applyClasses(drawResult.element, drawResult.style)
        }

        const complexWrapper = document.createElement('div')
        complexWrapper.classList.add('complewrapper')
        this.createExportSelectionControl(complexWrapper, result)
        complexWrapper.appendChild(drawResult.element)
        this.display.appendChild(complexWrapper)
        renderedCount++
      }
    }
    this.scheduleNarrowLabelVisibility()
    if (renderedCount === 0) {
      this.setStatusBanner('results', 'empty', 'No results match this filter.')
    }
  }

  /**
   * Draw the boxes of a result
   * @date 2/12/2024 - 7:22:10 PM
   *
   * @param {*} result the result you want to draw
   * @returns {*} An object containing the HTML element and a list of styles that can be applied to the container
   */
  drawResultBoxes (result) {
    const getSizeAndCounter = (result) => {
      const res = { size: 0, counter: 0 }
      if (result.ResultMetaData && result.ResultMetaData.ResultCounters) {
        const counterList = result.ResultMetaData.ResultCounters
        if (counterList) {
          for (const c of counterList) {
            if (c.CounterType === '2') {
              res.size = c.CounterValue
            } else if (c.CounterType === '3') {
              res.counter = c.CounterValue
            }
          }
        }
      }
      return res
    }

    if (!result) {
      return
    }
    // const classification = result.ResultMetaData.Classification
    const top = document.createElement('div')
    top.classList.add('resultBoxLabel')
    const children = []

    const counterInfo = getSizeAndCounter(result)
    const style = this.getStyle(result)

    if (result.isReference) {
      this.setLabelText(top, `Ref ID: ${result.ResultMetaData.ResultId}`)
    } else if (!result.id) {
      // console.log('OTHER')
      return
    } else {
      const resultLabelText = this.getResultBoxLabelText(result)
      if (resultLabelText) {
        this.setLabelText(top, resultLabelText)
      } else if (result.ResultMetaData.CreationTime) {
        this.setLabelText(top, `Other: ${result.id}`)
      } else {
        this.setLabelText(top, `Ref: ${result.id}`)
      }

      /*
      if (result.ClientData.rebuildState) {
        top.innerText += ' '
        if (result.ClientData.rebuildState.claimed) { top.innerText += 'C' }
        if (result.ClientData.rebuildState.resolved) { top.innerText += 'R' }
        if (result.ClientData.rebuildState.partial) { top.innerText += 'P' }
      } */

      if (counterInfo.size > 0) {
        this.setLabelText(top, `${top.textContent} [${counterInfo.counter}/${counterInfo.size}]`)
      }
      this.setLabelText(top, this.wrapBeforeResultText(top.textContent))
      top._fullText = top.textContent

      const contentList = result.ResultContent

      if (contentList) {
        for (const content of contentList) {
          const childBox = this.drawResultBoxes(content)
          if (childBox) {
            children.push(childBox)
          }
        }
      }
    }

    if (this.envelope !== 'true') {
      this.applyClasses(top, style)
    }

    return {
      element: this.makeRoot(
        top,
        children,
        counterInfo.counter,
        counterInfo.size,
        this.envelope === 'true'),
      style
    }
  }

  /**
   * Decide how a result should look and how its children should be stacked
   * @date 2/2/2024 - 8:40:57 AM
   *
   * @param {*} result the result that we want to decide how it should look
   * @returns {*} a list of styles that should be applied to itself or its parent
   */
  getStyle (result) {
    const style = []
    if (result.isPartial) {
      style.push('resPartial')
    } else {
      style.push('resFull')
    }
    if (!result.evaluation) {
      style.push('resNOK')
    } else {
      // style.push('resOK')
    }

    // Fade out the shadow on new results
    const secondsOld = (new Date().getTime() - result.clientLatestRecievedTime) / 1000
    if (this.envelope !== 'true') {
      if (secondsOld < 15) {
        style.push('resNew4')
      } else if (secondsOld < 30) {
        style.push('resNew3')
      } else if (secondsOld < 45) {
        style.push('resNew2')
      } else if (secondsOld < 60) {
        style.push('resNew1')
      }
    }

    if (result.isReference) {
      style.push('resReference')
    } else {
      switch (parseInt(result.classification)) {
        case 1:
          style.push('resTightening')
          if (!result.evaluation) {
            style.push('resNOK')
          }
          break
        case 3:
          style.push('resBatch')
          break
        case 4:
          style.push('resJob')
          break
        default:
          style.push('resOther')
      }
    }

    return style
  }
}
