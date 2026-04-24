import BasicScreen from './basic-screen.mjs' // Basic functionality application code for the screen functionality
import { lowerCaseJsonKeys } from './json-key-normalization.mjs'
import {
  DEFAULT_RESULT_SESSION_AUTO_RESTORE,
  DEFAULT_RESULT_SESSION_AUTO_SAVE,
  RESULT_SESSION_STORAGE_KEY
} from '../../ijt-support/results/result-storage-constants.mjs'

const FADE_TIME_MS = 10_000
const FADE_STEPS = 5
const DEFAULT_MAX_STORED_RESULTS = 200

/**
 * The purpose of this class is to generate an GUI
 * for editing settings used elsewhere in the app
 **/
export default class Settings extends BasicScreen {
  constructor (webSocketManager) {
    super('Settings')
    this.tabHelpText = 'Configure default product, program, joint, and initial view-level preferences.'
    this.loaded = false
    this.resolvers = []

    this.webSocketManager = webSocketManager
    this.productId = '-'
    this.JoiningProcess1 = '-'
    this.JoiningProcess2 = '-'
    this.Joint1 = '-'
    this.Joint2 = '-'
    this.maxStoredResults = DEFAULT_MAX_STORED_RESULTS
    this.resultSessionAutoSave = DEFAULT_RESULT_SESSION_AUTO_SAVE
    this.resultSessionAutoRestore = DEFAULT_RESULT_SESSION_AUTO_RESTORE

    this.settings = { // default values
      productid: 'www.company.com/ProductABC123',
      button1selection: 'SourceTightening_Identifier_1',
      button2selection: 'SourceTightening_Identifier_2',
      button1joint: 'Joint_1',
      button2joint: 'Joint_2',
      initialviewlevel: 4,
      maxstoredresults: DEFAULT_MAX_STORED_RESULTS,
      resultsessionautosave: DEFAULT_RESULT_SESSION_AUTO_SAVE,
      resultsessionautorestore: DEFAULT_RESULT_SESSION_AUTO_RESTORE,
      command: 'set settings',
      endpoint: 'common'
    }

    // Listen to the tree of possible connection points (Available OPC UA servers)
    this.webSocketManager.subscribe(null, 'get settings', (msg) => {
      this.setupPage(msg)
    })

    this.webSocketManager.send('get settings')

    this.fadeList = {}
    this.fadeTime = FADE_TIME_MS
    this.fadeSteps = FADE_STEPS

    this.refreshTraceCallbackFade = (trace, traceOwner) => {
      const fadeFunc = () => {
        if (trace.fadeCounter < 1) {
          traceOwner.deleteSelected(trace)
          this.fadeList[trace.resultId] = false
        } else {
          trace.fadeCounter--
          trace.fade(1 / (this.fadeSteps + 1))
          setTimeout(fadeFunc, this.fadeTime / this.fadeSteps)
        }
      }
      const currentCounter = this.fadeList[trace.resultId]
      if (!currentCounter) {
        this.fadeList[trace.resultId] = true
        trace.fadeCounter = this.fadeSteps
        setTimeout(fadeFunc, this.fadeTime / this.fadeSteps)
      }
    }

    this.refreshTraceCallback = (trace, traceOwner) => {
      traceOwner.deleteSelected(trace)
    }

    const editArea = document.createElement('div')
    editArea.classList.add('demosettingArea')
    this.backGround.appendChild(editArea)

    this.displayArea = document.createElement('div')
    this.backGround.appendChild(this.displayArea)

    this.container = editArea

    this.createButton('Save', this.displayArea, () => {
      if (this.productId) {
        this.settings.productid = this.productId
      }
      if (this.JoiningProcess1) {
        this.settings.button1selection = this.JoiningProcess1
      }
      if (this.Joint1) {
        this.settings.button1joint = this.Joint1
      }
      if (this.Joint2) {
        this.settings.button2joint = this.Joint2
      }
      if (this.JoiningProcess2) {
        this.settings.button2selection = this.JoiningProcess2
      }
      if (this.initialViewLevel) {
        this.settings.initialviewlevel = this.initialViewLevel
      }
      this.settings.maxstoredresults = this.getMaxStoredResults()
      this.settings.resultsessionautosave = this.getResultSessionAutoSave()
      this.settings.resultsessionautorestore = this.getResultSessionAutoRestore()
      this.webSocketManager.send('set settings', null, null, this.settings)
    })

    this.createButton('Clear local result session', this.displayArea, () => {
      this.clearLocalResultSession()
    })

    this.setupPage(this.settings, true)

    // this.container.innerHTML += '<p>ProductId'
  }

  setupPage (msg, initial) {
    const normalizedMsg = lowerCaseJsonKeys(msg) || {}

    if (normalizedMsg.productid !== undefined ||
        normalizedMsg.initialviewlevel !== undefined ||
        normalizedMsg.maxstoredresults !== undefined) {
      this.settings = { ...this.settings, ...normalizedMsg }
      if (normalizedMsg.productid !== undefined) {
        this.productId = normalizedMsg.productid
      }
      if (normalizedMsg.button1selection !== undefined) {
        this.JoiningProcess1 = normalizedMsg.button1selection
      }
      if (normalizedMsg.button2selection !== undefined) {
        this.JoiningProcess2 = normalizedMsg.button2selection
      }
      if (normalizedMsg.button1joint !== undefined) {
        this.Joint1 = normalizedMsg.button1joint
      }
      if (normalizedMsg.button2joint !== undefined) {
        this.Joint2 = normalizedMsg.button2joint
      }
      if (normalizedMsg.methoddefaults !== undefined) {
        this.methodDefaults = normalizedMsg.methoddefaults
      }
      if (normalizedMsg.initialviewlevel !== undefined) {
        this.initialViewLevel = normalizedMsg.initialviewlevel
      }
      if (normalizedMsg.maxstoredresults !== undefined) {
        this.maxStoredResults = this.normalizeMaxStoredResults(normalizedMsg.maxstoredresults)
      } else {
        this.maxStoredResults = this.normalizeMaxStoredResults(this.settings.maxstoredresults)
      }
      if (normalizedMsg.resultsessionautosave !== undefined) {
        this.resultSessionAutoSave = this.normalizeBooleanSetting(normalizedMsg.resultsessionautosave, DEFAULT_RESULT_SESSION_AUTO_SAVE)
      } else {
        this.resultSessionAutoSave = this.normalizeBooleanSetting(this.settings.resultsessionautosave, DEFAULT_RESULT_SESSION_AUTO_SAVE)
      }
      if (normalizedMsg.resultsessionautorestore !== undefined) {
        this.resultSessionAutoRestore = this.normalizeBooleanSetting(normalizedMsg.resultsessionautorestore, DEFAULT_RESULT_SESSION_AUTO_RESTORE)
      } else {
        this.resultSessionAutoRestore = this.normalizeBooleanSetting(this.settings.resultsessionautorestore, DEFAULT_RESULT_SESSION_AUTO_RESTORE)
      }
      if (normalizedMsg.envelope !== undefined) {
        this.envelope = normalizedMsg.envelope
      }
    }

    try {
      this.container.innerHTML = ''

      const labelElement = document.createElement('label')
      labelElement.textContent = 'ProductId   '
      this.container.appendChild(labelElement)

      this.createInput(this.productId, this.container, (evt) => {
        this.productId = evt
      }, '40')
      this.container.appendChild(document.createElement('br'))

      const labelElement2 = document.createElement('label')
      labelElement2.textContent = 'Button 1 selection   '
      this.container.appendChild(labelElement2)

      this.createInput(this.JoiningProcess1, this.container, (evt) => {
        this.JoiningProcess1 = evt
      }, '40')
      this.container.appendChild(document.createElement('br'))

      const labelElement3 = document.createElement('label')
      labelElement3.textContent = 'Button 2 selection   '
      this.container.appendChild(labelElement3)

      this.createInput(this.JoiningProcess2, this.container, (evt) => {
        this.JoiningProcess2 = evt
      }, '40')
      this.container.appendChild(document.createElement('br'))

      const labelElement31 = document.createElement('label')
      labelElement31.textContent = 'Joint 1 identity   '
      this.container.appendChild(labelElement31)

      this.createInput(this.Joint1, this.container, (evt) => {
        this.Joint1 = evt
      }, '40')
      this.container.appendChild(document.createElement('br'))

      const labelElement32 = document.createElement('label')
      labelElement32.textContent = 'Joint 2 identity   '
      this.container.appendChild(labelElement32)

      this.createInput(this.Joint2, this.container, (evt) => {
        this.Joint2 = evt
      }, '40')
      this.container.appendChild(document.createElement('br'))

      const labelElement4 = document.createElement('label')
      labelElement4.textContent = 'Default view level   '
      this.container.appendChild(labelElement4)

      this.container.select = document.createElement('select')
      this.container.appendChild(this.container.select)

      const viewLevels = [['Basic', 1], ['Simple', 2], ['Detailed', 3], ['Specialized', 4], ['Settings', 5]]

      for (const optionData of viewLevels) {
        const option = document.createElement('option')
        option.value = optionData[1]
        option.textContent = optionData[0]
        this.container.select.appendChild(option)
      }

      this.container.select.value = this.initialViewLevel

      this.container.select.onchange = (evt) => {
        this.initialViewLevel = evt.target.value
      }

      this.container.appendChild(document.createElement('br'))

      const labelElement5 = document.createElement('label')
      labelElement5.textContent = 'Max stored results   '
      this.container.appendChild(labelElement5)
      this.createInput(String(this.getMaxStoredResults()), this.container, (evt) => {
        this.maxStoredResults = this.normalizeMaxStoredResults(evt)
      }, '20')
      this.container.appendChild(document.createElement('br'))

      const autoSaveLabel = document.createElement('label')
      autoSaveLabel.textContent = 'Result session auto-save   '
      this.container.appendChild(autoSaveLabel)
      const autoSaveCheckbox = this.createCheckbox(this.getResultSessionAutoSave(), (checked) => {
        this.resultSessionAutoSave = !!checked
      })
      this.container.appendChild(autoSaveCheckbox)
      this.container.appendChild(document.createElement('br'))

      const autoRestoreLabel = document.createElement('label')
      autoRestoreLabel.textContent = 'Result session auto-restore   '
      this.container.appendChild(autoRestoreLabel)
      const autoRestoreCheckbox = this.createCheckbox(this.getResultSessionAutoRestore(), (checked) => {
        this.resultSessionAutoRestore = !!checked
      })
      this.container.appendChild(autoRestoreCheckbox)
      this.container.appendChild(document.createElement('br'))
    } finally {
      if (!initial) {
        this.loaded = true
        for (const resolve of this.resolvers) {
          resolve(this)
        }
      }
    }
  }

  settingPromise () {
    // console.log('LOOKING FOR: '+nodeId+path)
    return new Promise((resolve, reject) => {
      if (this.loaded) {
        resolve(this)
      } else {
        this.resolvers.push(resolve)
      }
    })
  }

  normalizeMaxStoredResults (value) {
    const parsed = Number.parseInt(value, 10)
    if (!Number.isFinite(parsed) || parsed < 1) {
      return DEFAULT_MAX_STORED_RESULTS
    }
    return parsed
  }

  getMaxStoredResults () {
    return this.normalizeMaxStoredResults(this.maxStoredResults)
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

  getResultSessionAutoSave () {
    return this.normalizeBooleanSetting(this.resultSessionAutoSave, DEFAULT_RESULT_SESSION_AUTO_SAVE)
  }

  getResultSessionAutoRestore () {
    return this.normalizeBooleanSetting(this.resultSessionAutoRestore, DEFAULT_RESULT_SESSION_AUTO_RESTORE)
  }

  clearLocalResultSession () {
    this.ensureStatusBanner('settings')
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.removeItem(RESULT_SESSION_STORAGE_KEY)
      }
      this.setStatusBanner('settings', 'success', 'Cleared local result session storage.')
    } catch (_error) {
      this.setStatusBanner('settings', 'error', 'Unable to clear local result session storage.')
    }
  }
}
