/**
 * The purpose of this class is to display a GUI for filling in arguments and calling a method
 */
import { ijtLog } from '../../ijt-support/ijt-logger.mjs'

/** Result-type options for SimulateSingleResult / SimulateBulkResults */
const RESULT_TYPE_OPTIONS = [
  ['ONE_STEP_OK (0)', 0],
  ['ONE_STEP_NOK (1)', 1],
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
  createMethodArea (pathName) {
    const methodData = this.methodManager.getMethod(pathName)

    const buttonPress = (button) => {
      // Load argument values
      const values = []
      for (const argValue of button.listOfValuegrabbers) {
        values.push(argValue())
      }
      // This is when the actual call is made
      this.methodManager.call(methodData, values).then(
        (success) => {
          this.screen.messageDisplay(JSON.stringify(success))
        },
        (fail) => {
          this.screen.messageDisplay(JSON.stringify(fail))
        }
      )
    }

    // Setting up method area
    const methodNode = methodData.methodNode
    const area = this.screen.createArea(methodNode.displayName)
    area.classList.add('methodBorder')
    const titleLabel = this.screen.createLabel(methodNode.displayName)
    area.appendChild(titleLabel)

    try {
      let defaults
      if (this.settings?.methodDefaults) {
        defaults = this.settings.methodDefaults[methodData.methodNode.nodeIdString]
      }

      // Setting up argument windows
      const listOfValuegrabbers = []
      for (let index = 0; index < methodData.arguments.length; index++) {
        const arg = methodData.arguments[index]
        const lineArea = this.screen.createArea()
        lineArea.classList.add('methodRowDistance')
        area.appendChild(lineArea)
        listOfValuegrabbers.push(this.createMethodInput(arg, lineArea, defaults?.arguments[index], undefined, methodData.methodNode.displayName, index))
      }

      // Create the actual button for the call
      const button = this.screen.createButton('Call', area, buttonPress)

      button.listOfValuegrabbers = listOfValuegrabbers

      if (defaults?.autocall) {
        buttonPress(button)
      }
    } catch (error) {
      area.classList.add('errorBackground')
      const errorArea = this.screen.createArea()
      errorArea.innerText = `${error.name} : ${error.message}`
      ijtLog.error(`${error.name} : ${error.message}`)
      area.appendChild(errorArea)
    }
    return area
  }

  /**
   * Apply well-known default values by argument name when no explicit default is provided.
   * All Boolean arguments implicitly default to true (handled in the Boolean case below).
   */
  _applyNamedDefaults (arg, defaultValue) {
    if (defaultValue !== '' && typeof defaultValue !== 'undefined') return defaultValue
    const name = arg?.Name ?? ''
    // Simulation — result type & traces
    if (name === 'Result Type') return 2
    if (name === 'Include Traces') return true
    if (name === 'Include Traces For Child Results') return true
    // Batch/Sync/Job — references
    if (name === 'Send Child Results as References (Recommended)') return true
    if (name === 'Send Child Results as References') return true
    // Bulk results defaults
    if (name === 'From Sequence Number') return 1
    if (name === 'To Sequence Number') return 10
    if (name === 'Duration Between Results') return 100
    if (name === 'Number Of Results') return 3
    if (name === 'Update Result Variables') return true
    // Joining process management defaults
    if (name === 'Counter Size' || name === 'Counter Value') return 1
    if (name === 'Increment Count' || name === 'Decrement Count') return 1
    return defaultValue
  }

  /**
   * Create an input field that helps in the invocation of a method
   * @param {*} arg the argument that you want the data for
   * @param {*} area the area where the input field should go
   * @param {*} defaultValue optional pre-filled value
   * @param {*} callback optional onchange callback
   * @returns a function that returns {value, type} when called
   */
  createMethodInput (arg, area, defaultValue = '', callback) {
    const dataTypeId = String(arg?.DataType?.Identifier ?? '')
    defaultValue = this._applyNamedDefaults(arg, defaultValue)

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
        drop.classList.add('inputStyle', 'methodInput')
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
        let entityList = []
        const entityListDiv = document.createElement('div')
        selectionArea.appendChild(entityListDiv)

        this.screen.createButton('Add identifier', selectionArea, () => {
          const selectionDiv = this.entityManager?.makeSelectableEntityView((x, entity) => {
            selectionArea.removeChild(selectionDiv)
            selectionArea.removeChild(selectionAreaBackground)
            entityListDiv.classList.add('rows')
            entityList.push(entity)
            entityListDiv.innerHTML = ''
            for (const ent of entityList) {
              const entityArea = this.screen.createLabel(`${ent.Name}(${ent.EntityId})`)
              entityArea.classList.add('indent')
              entityListDiv.appendChild(entityArea)
            }
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
              Name: entity.name,
              Description: entity.description,
              EntityId: entity.entityId,
              EntityOriginId: entity.entityOriginId,
              IsExternal: entity.isExternal,
              EntityType: entity.entityType,
            },
          }))
          entityList = []
          entityListDiv.innerText = ''
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
        if (arg?.Name === 'Result Type') {
          const drop = this.screen.createDropdown('', null)
          drop.classList.add('inputStyle', 'methodInput')
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
        if (arg?.Name === 'Classification') {
          const drop = this.screen.createDropdown('', null)
          drop.classList.add('inputStyle', 'methodInput')
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
