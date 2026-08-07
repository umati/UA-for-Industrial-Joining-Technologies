/**
 * The purpose of this class is to display a GUI for filling in arguments and calling a method
 */
import { ijtLog } from '../../ijt-support/ijt-logger.mjs'
import {
  clearMethodValues,
  loadMethodValues,
  saveMethodValues
} from '../../ijt-support/methods/method-preset-store.mjs'

/** Result-type options for SimulateSingleResult / SimulateBulkResults */
const RESULT_TYPE_OPTIONS = [
  ['SIMPLE_OK (0)', 0],
  ['SINGLE_STEP_OK (1)', 1],
  ['MULTI_STEP_OK (2)', 2],
  ['MULTI_STEP_NOK — Failed Step (3)', 3],
  ['MULTI_STEP_NOK — Trigger Lost (4)', 4],
]

/** Classification options for SimulateBatch_Or_Sync_Result
 *  Values from CommonSystemData_t::ResultClassification:
 *  SYNC_RESULT = 2, BATCH_RESULT = 3 */
const CLASSIFICATION_OPTIONS = [
  ['BATCH (3)', 3],
  ['SYNC (2)', 2],
]

export default class MethodGUICreator {
  constructor (screen, methodManager, entityManager, settings) {
    this.methodManager = methodManager
    this.entityManager = entityManager
    this.settings = settings
    this.screen = screen
  }

  /**
   * Given method data, create a button and input fields in an area
   * @param {*} methodData data about the method from the method manager
   */
  createMethodArea (pathName, { profile = 'last-used' } = {}) {
    const methodData = this.methodManager.getMethod(pathName)
    const methodMetadata = methodData?.metadata || {}
    const methodStorageKey = methodData?.nodeIdString || methodData?.methodNode?.nodeIdString || pathName
    const storedValues = loadMethodValues(methodStorageKey)
    const savedValues = profile === 'last-used' ? storedValues : null

    const buttonPress = (button) => {
      // Load argument values
      const values = []
      for (const argValue of button.listOfValuegrabbers) {
        values.push(argValue())
      }
      saveMethodValues(methodStorageKey, values)
      // This is when the actual call is made
      this.methodManager.call(methodData, values).then(
        (success) => {
          this.screen.messageDisplay(this.formatMethodResult(pathName, success))
        },
        (fail) => {
          this.screen.messageDisplay(this.formatMethodResult(pathName, fail))
        }
      )
    }

    // Setting up method area
    const methodNode = methodData.methodNode
    const area = document.createElement('details')
    area.classList.add('methodBorder')
    const summary = document.createElement('summary')
    summary.classList.add('methodCardSummary')
    const titleLabel = document.createElement('span')
    titleLabel.classList.add('methodCardTitle')
    titleLabel.textContent = methodNode.displayName
    summary.appendChild(titleLabel)
    area.appendChild(summary)

    const content = document.createElement('div')
    content.classList.add('methodCardContent')
    area.appendChild(content)

    try {
      let defaults
      if (this.settings?.methodDefaults) {
        defaults = this.settings.methodDefaults[methodData.methodNode.nodeIdString]
      }

      if (Array.isArray(methodMetadata.notes) && methodMetadata.notes.length > 0) {
        const notes = document.createElement('div')
        notes.classList.add('methodHints')
        notes.textContent = methodMetadata.notes.join(' ')
        content.appendChild(notes)
      }

      const profileArea = document.createElement('div')
      profileArea.classList.add('methodPresetRow')
      const profileLabel = this.screen.createLabel('Values')
      profileLabel.classList.add('methodLabel')
      const profileSelect = document.createElement('select')
      profileSelect.classList.add('methodInput')
      const defaultOption = document.createElement('option')
      defaultOption.value = 'defaults'
      defaultOption.textContent = 'Recommended defaults'
      const savedOption = document.createElement('option')
      savedOption.value = 'last-used'
      savedOption.textContent = 'Last used values'
      savedOption.disabled = !storedValues
      profileSelect.add(defaultOption)
      profileSelect.add(savedOption)
      profileSelect.value = profile
      profileSelect.addEventListener('change', () => {
        const replacement = this.createMethodArea(pathName, { profile: profileSelect.value })
        area.replaceWith(replacement)
      })
      profileArea.append(profileLabel, profileSelect)
      content.appendChild(profileArea)

      // Setting up argument windows
      const listOfValuegrabbers = []
      for (let index = 0; index < methodData.arguments.length; index++) {
        const arg = methodData.arguments[index]
        const lineArea = this.screen.createArea()
        lineArea.classList.add('methodRowDistance')
        content.appendChild(lineArea)
        const metadataDefault = this.getMetadataDefault(methodMetadata?.defaults, arg?.Name)
        const savedValue = this.getSavedArgumentValue(savedValues?.[index], arg)
        const configuredDefault = profile === 'last-used' && typeof savedValue !== 'undefined'
          ? savedValue
          : defaults?.arguments?.[index]
        listOfValuegrabbers.push(this.createMethodInput(arg, lineArea, configuredDefault, undefined, methodData.methodNode.displayName, index, metadataDefault))
      }

      // Create the actual button for the call
      const button = this.screen.createButton('Call', content, buttonPress)

      button.listOfValuegrabbers = listOfValuegrabbers
      this.screen.createButton('Save values', content, () => {
        saveMethodValues(methodStorageKey, listOfValuegrabbers.map(grabber => grabber()))
      })
      this.screen.createButton('Clear saved values', content, () => {
        clearMethodValues(methodStorageKey)
        const replacement = this.createMethodArea(pathName, { profile: 'defaults' })
        area.replaceWith(replacement)
      })

      if (defaults?.autocall) {
        buttonPress(button)
      }
    } catch (error) {
      area.classList.add('errorBackground')
      const errorArea = this.screen.createArea()
      errorArea.innerText = `${error.name} : ${error.message}`
      ijtLog.error(`${error.name} : ${error.message}`)
      content.appendChild(errorArea)
    }
    return area
  }

  getSavedArgumentValue (savedArgument, arg) {
    if (!savedArgument || typeof savedArgument !== 'object') return undefined
    const expectedType = String(arg?.DataType?.Identifier ?? '')
    const savedType = String(savedArgument?.type?.Identifier ?? '')
    if (expectedType && savedType && expectedType !== savedType) return undefined
    const value = savedArgument.value
    if (Array.isArray(value) || (value && typeof value === 'object' && expectedType !== '21')) return undefined
    return value
  }

  /**
   * Apply well-known default values by argument name when no explicit default is provided.
   * All Boolean arguments implicitly default to true (handled in the Boolean case below).
   */
  _applyNamedDefaults (arg, defaultValue, methodName = '', argumentIndex = 0) {
    if (defaultValue !== '' && typeof defaultValue !== 'undefined') return defaultValue
    const name = arg?.Name ?? ''
    const normalizedName = String(name).replace(/\s+/g, '').toLowerCase()
    const normalizedMethod = String(methodName).replace(/[_\s]+/g, '').toLowerCase()
    // Simulation — result type & traces
    if (normalizedName === 'resulttype') return 2
    if (normalizedName === 'classification' || normalizedName.endsWith('classification')) return 3
    if (normalizedName === 'productinstanceuri') {
      return this.resolveMetadataDefault({ source: 'productid', allowEmpty: true })
    }
    if (normalizedName === 'includetraces') return true
    if (normalizedName === 'includetracesforchildresults') return true
    if (normalizedName === 'eventtype') return 1
    if ((normalizedMethod === 'simulateevents' || normalizedMethod === 'simulateconditions') && argumentIndex === 0) return 1
    if (normalizedMethod === 'simulatebulkevents') return argumentIndex === 0 ? 1 : 3
    // Batch/Sync/Job — child count & references
    if (normalizedName === 'numberofchildresults') return 3
    if (normalizedName === 'sendchildresultsasreferencesrecommended') return true
    if (normalizedName === 'sendchildresultsasreferences') return true
    // Bulk results defaults
    if (normalizedName === 'fromsequencenumber') return 100
    if (normalizedName === 'tosequencenumber') return 150
    if (normalizedName === 'durationbetweenresults') return 100
    if (normalizedName === 'numberofresults') return 3
    if (normalizedName === 'updateresultvariables') return true
    // Joining process management defaults
    if (normalizedName === 'countersize' || normalizedName === 'countervalue') return 1
    if (normalizedName === 'incrementcount' || normalizedName === 'decrementcount') return 1
    if (['2', '3', '4', '5', '6', '7', '8', '9', '10', '11'].includes(String(arg?.DataType?.Identifier))) {
      return this.methodManager?.methodMetadata?.globalDefaults?.integerFallback ?? 1
    }
    if (String(arg?.DataType?.Identifier) === '12') {
      return this.methodManager?.methodMetadata?.globalDefaults?.stringFallback ?? 'Sample'
    }
    return defaultValue
  }

  getMetadataDefault (defaults, argumentName) {
    if (!defaults || !argumentName) return undefined
    if (Object.hasOwn(defaults, argumentName)) return defaults[argumentName]

    const normalizedArgumentName = String(argumentName).replace(/[^a-z0-9]/gi, '').toLowerCase()
    const matchingKey = Object.keys(defaults)
      .map(key => ({ key, normalized: key.replace(/[^a-z0-9]/gi, '').toLowerCase() }))
      .filter(candidate => candidate.normalized === normalizedArgumentName ||
        normalizedArgumentName.endsWith(candidate.normalized))
      .sort((left, right) => right.normalized.length - left.normalized.length)[0]?.key
    return matchingKey ? defaults[matchingKey] : undefined
  }

  resolveMetadataDefault (metadataDefault) {
    if (metadataDefault && typeof metadataDefault === 'object' && metadataDefault.source === 'currentUtc') {
      return new Date().toISOString()
    }
    if (metadataDefault && typeof metadataDefault === 'object' && metadataDefault.source === 'productid') {
      const value = String(
        this.settings?.methodProductInstanceUri ||
        this.settings?.productId ||
        this.settings?.productid ||
        ''
      ).trim()
      if (value && !value.includes('www.company.com/ProductABC123')) {
        return value
      }
      return metadataDefault.allowEmpty ? '' : value
    }
    return metadataDefault
  }

  formatMethodResult (methodName, payload) {
    const result = {
      method: methodName,
      timestamp: new Date().toISOString(),
      payload
    }
    return JSON.stringify(result, null, 2)
  }

  /**
   * Create an input field that helps in the invocation of a method
   * @param {*} arg the argument that you want the data for
   * @param {*} area the area where the input field should go
   * @param {*} defaultValue optional pre-filled value
   * @param {*} callback optional onchange callback
   * @returns a function that returns {value, type} when called
   */
  createMethodInput (arg, area, defaultValue = '', callback, methodName = '', argumentIndex = 0, metadataDefault) {
    const dataTypeId = String(arg?.DataType?.Identifier ?? '')
    const normalizedArgumentName = String(arg?.Name ?? '').replace(/[^a-z0-9]/gi, '').toLowerCase()
    const resolvedMetadataDefault = this.resolveMetadataDefault(metadataDefault)
    if ((defaultValue === '' || typeof defaultValue === 'undefined') && typeof resolvedMetadataDefault !== 'undefined') {
      defaultValue = resolvedMetadataDefault
    }
    defaultValue = this._applyNamedDefaults(arg, defaultValue, methodName, argumentIndex)

    // Argument label
    if (arg.Name && arg.Name.length > 0) {
      const titleLabel = this.screen.createLabel(`${arg.Name}  `)
      titleLabel.classList.add('methodLabel')
      area.appendChild(titleLabel)
    }

    const descText = arg?.Description?.Text ?? arg?.Description?._text ?? ''

    switch (dataTypeId) {
      // ── DropDown (custom virtual type) ─────────────────────────────────────
      case 'DropDown': {
        const drop = this.screen.createDropdown('', (x) => {
          if (callback) callback(x)
        })
        drop.classList.add('inputStyle', 'methodInput', 'methodDropdownWrap')
        for (let i = 0; i < Object.values(arg.Options).length; i++) {
          drop.addOption(Object.values(arg.Options)[i], Object.keys(arg.Options)[i])
        }
        drop.select.selectedIndex = defaultValue
        area.appendChild(drop)
        return function () { return { value: drop.value } }
      }

      // ── JoiningProcessIdentification (IJT custom type 3029) ────────────────
      case '3029': {
        const selectionArea = document.createElement('div')
        selectionArea.classList.add('methodInputRight')
        area.appendChild(selectionArea)

        const drop = this.screen.createDropdown('Type', () => {}, 'dropJoiningProcess')
        drop.classList.add('methodDropdownWrap')
        drop.addOption('OriginId', 1)
        drop.addOption('Specific Id', 0)
        drop.addOption('Selection name', 2)
        selectionArea.appendChild(drop)

        selectionArea.appendChild(this.screen.createLabel('Value'))
        const sel = this.screen.createInput('', selectionArea, callback, 55)
        sel.dataType = arg.DataType
        sel.title = `Datatype: JoiningProcessId\n${descText}`
        sel.value = 0

        return function () {
          const value = []
          for (let i = 0; i < 3; i++) {
            value.push(parseInt(drop.select.value) === i
              ? { value: sel.value, type: '31918' }
              : { value: '', type: '31918' })
          }
          return { type: { Identifier: '3029', NamespaceIndex: '3' }, structure: 'JoiningProcessIdentification', value }
        }
      }

      // ── EntityDataType array (IJT custom type 3010) ────────────────────────
      case '3010': {
        const selectionArea = document.createElement('div')
        area.appendChild(selectionArea)
        const entityList = []
        const entityListDiv = document.createElement('div')
        selectionArea.appendChild(entityListDiv)

        const renderEntities = () => {
          entityListDiv.replaceChildren()
          entityListDiv.classList.toggle('rows', entityList.length > 0)
          for (const [entityIndex, ent] of entityList.entries()) {
            const entityArea = document.createElement('div')
            entityArea.classList.add('methodEntityIdentifier')
            const entityName = ent.name ?? ent.Name ?? ''
            const entityId = ent.entityId ?? ent.EntityId ?? ''
            entityArea.appendChild(this.screen.createLabel(`${entityName} (${entityId})`))
            this.screen.createButton('Remove', entityArea, () => {
              entityList.splice(entityIndex, 1)
              renderEntities()
            })
            entityListDiv.appendChild(entityArea)
          }
        }

        this.screen.createButton('Add identifier', selectionArea, () => {
          const selectionDiv = this.entityManager?.makeSelectableEntityView((x, entity) => {
            selectionArea.removeChild(selectionDiv)
            selectionArea.removeChild(selectionAreaBackground)
            entityList.push(entity)
            renderEntities()
          }, 'Select an identifier entity')
          const selectionAreaBackground = document.createElement('div')
          selectionAreaBackground.classList.add('idSelectDialogGrayBackground')
          selectionArea.appendChild(selectionAreaBackground)
          selectionDiv.classList.add('idSelectDialog')
          selectionArea.appendChild(selectionDiv)
        })

        return function () {
          const value = entityList.map((entity) => ({
            value: {
              Name: entity.name ?? entity.Name,
              Description: entity.description ?? entity.Description,
              EntityId: entity.entityId ?? entity.EntityId,
              EntityOriginId: entity.entityOriginId ?? entity.EntityOriginId,
              IsExternal: entity.isExternal ?? entity.IsExternal,
              EntityType: entity.entityType ?? entity.EntityType,
            },
          }))
          return { type: { Identifier: '3010', NamespaceIndex: '3' }, structure: 'EntityDataType', value }
        }
      }

      // ── Boolean — checkbox, always defaults to TRUE ────────────────────────
      case '1': {
        let returnValue = true
        if (typeof defaultValue !== 'undefined' && defaultValue !== '') {
          returnValue = defaultValue === true || defaultValue === 'true'
        }
        const cb = this.screen.createCheckbox(returnValue, (newValue) => {
          returnValue = newValue
          if (callback) callback(newValue)
        })
        cb.dataType = arg.DataType
        cb.title = `Datatype: Boolean\n${descText}`
        area.appendChild(cb)
        return function () {
          return { value: returnValue, type: cb.dataType }
        }
      }

      // ── LocalizedText (OPC UA type 21) ─────────────────────────────────────
      case '21': {
        const wrapper = document.createElement('div')
        wrapper.classList.add('methodInputRight')
        area.appendChild(wrapper)

        wrapper.appendChild(this.screen.createLabel('Text  '))
        const textInput = this.screen.createInput('', wrapper, null, 50)
        const defText = typeof defaultValue === 'object'
          ? (defaultValue?.Text ?? '')
          : (typeof defaultValue === 'string' ? defaultValue : '')
        textInput.value = defText
        textInput.title = `LocalizedText.Text\n${descText}`
        textInput.placeholder = 'Text value'

        wrapper.appendChild(this.screen.createLabel('  Locale  '))
        const localeInput = this.screen.createInput('en', wrapper, null, 10)
        localeInput.value = typeof defaultValue === 'object' ? (defaultValue?.Locale ?? 'en') : 'en'
        localeInput.title = 'LocalizedText.Locale — ISO language code (e.g. "en")'
        localeInput.placeholder = 'en'

        textInput.dataType = arg.DataType
        return function () {
          return {
            value: { Text: textInput.value, Locale: localeInput.value || 'en' },
            type: textInput.dataType,
          }
        }
      }

      // ── UInt32 (7) / Int32 (6) — with special dropdown for 'Result Type' ──
      case '6': // Int32
      case '7': { // UInt32
        if (normalizedArgumentName === 'resulttype') {
          const drop = this.screen.createDropdown('', null)
          drop.classList.add('inputStyle', 'methodInput', 'methodDropdownWrap')
          for (const [label, val] of RESULT_TYPE_OPTIONS) {
            drop.addOption(label, val)
          }
          drop.select.value = String(defaultValue ?? 2)
          area.appendChild(drop)
          return function () {
            return { value: parseInt(drop.select.value, 10), type: arg.DataType }
          }
        }
        const input67 = this.screen.createInput('', area, callback, 45)
        input67.dataType = arg.DataType
        input67.title = `Datatype: Number\n${descText}`
        input67.value = defaultValue
        return function () { return { value: input67.value, type: input67.dataType } }
      }

      // ── Byte (3) — with special dropdown for 'Classification' ─────────────
      case '3': {
        if (normalizedArgumentName === 'classification' || normalizedArgumentName.endsWith('classification')) {
          const drop = this.screen.createDropdown('', null)
          drop.classList.add('inputStyle', 'methodInput', 'methodDropdownWrap')
          for (const [label, val] of CLASSIFICATION_OPTIONS) {
            drop.addOption(label, val)
          }
          drop.select.value = String(defaultValue ?? 3)
          area.appendChild(drop)
          return function () {
            return { value: parseInt(drop.select.value, 10), type: arg.DataType }
          }
        }
        const input3 = this.screen.createInput('', area, callback, 45)
        input3.dataType = arg.DataType
        input3.title = `Datatype: Number\n${descText}`
        input3.value = defaultValue
        return function () { return { value: input3.value, type: input3.dataType } }
      }

      // ── Int64 (8) / UInt64 (9) ─────────────────────────────────────────────
      case '8': // Int64
      case '9': { // UInt64
        const input89 = this.screen.createInput('', area, callback, 45)
        input89.dataType = arg.DataType
        input89.title = `Datatype: Number (64-bit)\n${descText}`
        input89.value = defaultValue
        return function () { return { value: input89.value, type: input89.dataType } }
      }

      // ── String (12) ────────────────────────────────────────────────────────
      case '12': {
        const input12 = this.screen.createInput('', area, callback, 45)
        input12.dataType = arg.DataType
        input12.title = `Datatype: String\n${descText}`
        input12.value = defaultValue
        return function () { return { value: input12.value, type: input12.dataType } }
      }

      // ── Default — plain text input ─────────────────────────────────────────
      default: {
        const inputDef = this.screen.createInput('', area, callback, 45)
        inputDef.dataType = arg.DataType
        inputDef.title = `Datatype: ${arg.DataType?.Identifier ?? '?'}\n${descText}`
        inputDef.value = defaultValue
        return function () { return { value: inputDef.value, type: inputDef.dataType } }
      }
    }
  }
}
