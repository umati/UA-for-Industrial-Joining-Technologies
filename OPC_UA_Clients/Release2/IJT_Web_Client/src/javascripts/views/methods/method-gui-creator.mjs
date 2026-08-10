/**
 * The purpose of this class is to display a GUI for filling in arguments and calling a method
 */
import { ijtLog } from '../../ijt-support/ijt-logger.mjs'
import {
  clearMethodValues,
  loadMethodPreferences,
  loadMethodValues,
  saveMethodPreferences,
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

const JOINING_PROCESS_IDENTIFICATION_MODES = Object.freeze([
  {
    label: 'Specific Id',
    index: 0,
    placeholder: 'Enter the exact JoiningProcess Id',
    help: 'Use the explicit JoiningProcess Id returned by the server.'
  },
  {
    label: 'OriginId',
    index: 1,
    placeholder: 'Enter the external/origin id',
    help: 'Use the external or origin identifier mapped by the server.'
  },
  {
    label: 'Selection name',
    index: 2,
    placeholder: 'Enter the selection name',
    help: 'Use a human-readable selection name configured on the server.'
  }
])

export default class MethodGUICreator {
  constructor (screen, methodManager, entityManager, settings, methodState = null) {
    this.methodManager = methodManager
    this.entityManager = entityManager
    this.settings = settings
    this.methodState = methodState || {
      productInstanceUri: '',
      detectedTools: [],
      detectedJoints: [],
      detectedJoiningProcesses: []
    }
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
    const storedPreferences = loadMethodPreferences(methodStorageKey)
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
          this.screen.messageDisplay(this.formatMethodResult(pathName, success, methodData))
        },
        (fail) => {
          this.screen.messageDisplay(this.formatMethodResult(pathName, fail, methodData))
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

      const schemaSection = this.buildMethodSchemaSection(methodData)
      if (schemaSection) {
        content.appendChild(schemaSection)
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

      if (this.methodState.detectedTools?.length || this.methodState.detectedJoints?.length || this.methodState.detectedJoiningProcesses?.length) {
        const discoveryHint = document.createElement('p')
        discoveryHint.classList.add('methodHelpText')
        discoveryHint.textContent = 'Live tool, joint, and joining-process discovery is available where the current method signature supports it.'
        content.appendChild(discoveryHint)
      }

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
        listOfValuegrabbers.push(this.createMethodInput(arg, lineArea, configuredDefault, undefined, methodData.methodNode.displayName, index, metadataDefault, {
          methodData,
          methodStorageKey,
          storedPreferences,
          profile
        }))
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
    if (Array.isArray(value)) {
      return this._expectsArrayArgument(arg) ? value : undefined
    }
    if (this._expectsArrayArgument(arg)) {
      return undefined
    }
    if (value && typeof value === 'object' && expectedType !== '21') return undefined
    if (this._isProductInstanceUriArgument(arg)) return undefined
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
      const liveToolValue = String(this.methodState.productInstanceUri || '').trim()
      if (liveToolValue) {
        return liveToolValue
      }
      return ''
    }
    return metadataDefault
  }

  _normalizeArgumentName (argumentName = '') {
    return String(argumentName).replace(/[^a-z0-9]/gi, '').toLowerCase()
  }

  _isProductInstanceUriArgument (arg) {
    return this._normalizeArgumentName(arg?.Name) === 'productinstanceuri'
  }

  _isJoiningProcessIdentificationArgument (arg) {
    return String(arg?.DataType?.Identifier ?? '') === '3029' ||
      this._normalizeArgumentName(arg?.Name).includes('joiningprocessidentification')
  }

  _isJointIdArgument (arg) {
    const normalized = this._normalizeArgumentName(arg?.Name)
    return normalized === 'jointid' || normalized.endsWith('jointid')
  }

  _isJoiningProcessSelectionArgument (arg) {
    return this._isJoiningProcessIdentificationArgument(arg)
  }

  _expectsArrayArgument (arg) {
    const valueRank = Number(arg?.ValueRank)
    return valueRank >= 0 || valueRank === -3
  }

  _isStringLikeArgument (arg) {
    const dataTypeId = String(arg?.DataType?.Identifier ?? '')
    return dataTypeId === '12' || dataTypeId === '13' || dataTypeId === '31918'
  }

  _resolveInputSource (arg, defaultValue, metadataDefault, profile) {
    if (profile === 'last-used' && typeof defaultValue !== 'undefined' && defaultValue !== '') {
      return 'saved-values'
    }
    if (this._isProductInstanceUriArgument(arg) && typeof defaultValue === 'string' && defaultValue.trim()) {
      return 'live-tool'
    }
    if (metadataDefault && typeof metadataDefault === 'object' && metadataDefault.source === 'currentUtc') {
      return 'recommended-default'
    }
    if (typeof defaultValue !== 'undefined' && defaultValue !== '' && defaultValue !== false) {
      return 'recommended-default'
    }
    return ''
  }

  _formatInputSource (source) {
    switch (source) {
      case 'live-tool':
        return 'Auto-filled from live Tool.ProductInstanceUri discovery.'
      case 'saved-values':
        return 'Loaded from the last values you saved for this method.'
      case 'recommended-default':
        return 'Using the recommended default for this argument.'
      default:
        return ''
    }
  }

  _createInputSourceHint (text, area) {
    if (!text) return
    const hint = document.createElement('p')
    hint.classList.add('methodInputSource')
    hint.textContent = text
    area.appendChild(hint)
  }

  _structureFieldDefinitions (arg) {
    const declaredFields = Array.isArray(arg?.FieldDefinitions) ? arg.FieldDefinitions : []
    if (declaredFields.length > 0) {
      return declaredFields.map(field => ({
        name: field?.name || field?.Name || '',
        label: field?.name || field?.Name || '',
        type: String(field?.dataType ?? field?.DataType?.Identifier ?? '12')
      })).filter(field => field.name)
    }
    if (String(arg?.DataType?.Identifier ?? '') === '3029') {
      return [
        { name: 'JoiningProcessId', label: 'Specific Id', type: '31918' },
        { name: 'JoiningProcessOriginId', label: 'OriginId', type: '31918' },
        { name: 'SelectionName', label: 'Selection name', type: '31918' }
      ]
    }
    return []
  }

  _createGenericStructureEditor (arg, area, defaultValue, descText) {
    const fields = this._structureFieldDefinitions(arg)
    if (fields.length === 0) return null

    const wrapper = document.createElement('div')
    wrapper.classList.add('methodInputRight', 'methodCompositeInput', 'methodStructureInput')
    area.appendChild(wrapper)

    const fieldInputs = []
    const defaultsByName = Array.isArray(defaultValue)
      ? Object.fromEntries(defaultValue.map((entry, index) => [fields[index]?.name, entry?.value ?? '']).filter(([name]) => name))
      : {}

    for (const field of fields) {
      const label = this.screen.createLabel(field.label)
      label.classList.add('methodLabel', 'methodSubLabel')
      wrapper.appendChild(label)
      const input = this.screen.createInput('', wrapper, null, 55)
      input.value = String(defaultsByName[field.name] ?? '')
      input.title = `${field.name}\n${descText}`
      fieldInputs.push({ field, input })
    }

    return function () {
      return {
        type: { Identifier: String(arg?.DataType?.Identifier ?? ''), NamespaceIndex: String(arg?.DataType?.NamespaceIndex ?? '3') },
        structure: arg?.DataType?.Name ?? 'Structure',
        value: fieldInputs.map(({ field, input }) => ({ value: input.value, type: field.type }))
      }
    }
  }

  _extractMethodResponse (payload, methodData = {}) {
    const declaredOutputArguments = Array.isArray(methodData?.outputArguments) ? methodData.outputArguments : []
    if (payload && typeof payload === 'object' && !Array.isArray(payload) &&
      (Object.hasOwn(payload, 'outputArguments') || Object.hasOwn(payload, 'rawOutput') || Object.hasOwn(payload, 'callStatus'))) {
      const outputArguments = Array.isArray(payload.outputArguments) && payload.outputArguments.length > 0
        ? payload.outputArguments
        : (Array.isArray(payload.rawOutput) ? payload.rawOutput : [])
      return {
        callStatus: payload.callStatus,
        statusCode: payload.statusCode,
        returnValue: payload.returnValue ?? undefined,
        outputArguments,
        rawPayload: typeof payload.rawOutput !== 'undefined' ? payload.rawOutput : payload
      }
    }
    const normalizedMessage = payload?.message
    if (normalizedMessage && typeof normalizedMessage === 'object' && !Array.isArray(normalizedMessage) &&
      (Object.hasOwn(normalizedMessage, 'outputArguments') ||
        Object.hasOwn(normalizedMessage, 'rawOutput') ||
        Object.hasOwn(normalizedMessage, 'callStatus'))) {
      const outputArguments = Array.isArray(normalizedMessage.outputArguments) && normalizedMessage.outputArguments.length > 0
        ? normalizedMessage.outputArguments
        : (Array.isArray(normalizedMessage.rawOutput) ? normalizedMessage.rawOutput : [])
      return {
        callStatus: normalizedMessage.callStatus,
        statusCode: normalizedMessage.statusCode,
        returnValue: normalizedMessage.returnValue ?? undefined,
        outputArguments,
        rawPayload: typeof normalizedMessage.rawOutput !== 'undefined' ? normalizedMessage.rawOutput : payload
      }
    }
    if (Array.isArray(payload)) {
      if (declaredOutputArguments.length > 0) {
        return {
          returnValue: undefined,
          outputArguments: payload,
          rawPayload: payload
        }
      }
      return {
        callStatus: undefined,
        statusCode: undefined,
        returnValue: payload.length > 0 ? payload[0] : undefined,
        outputArguments: payload.slice(1),
        rawPayload: payload
      }
    }

    const message = payload?.message ?? payload
    if (!message || typeof message !== 'object') {
      return {
        callStatus: undefined,
        statusCode: undefined,
        returnValue: undefined,
        outputArguments: [],
        rawPayload: payload
      }
    }

    const output = message.output
    if (typeof output === 'undefined' && Array.isArray(message)) {
      if (declaredOutputArguments.length > 0) {
        return {
          callStatus: undefined,
          statusCode: undefined,
          returnValue: undefined,
          outputArguments: message,
          rawPayload: payload
        }
      }
      return {
        callStatus: undefined,
        statusCode: undefined,
        returnValue: message.length > 0 ? message[0] : undefined,
        outputArguments: message.slice(1),
        rawPayload: payload
      }
    }

    let outputArguments = []
    if (Array.isArray(output)) {
      outputArguments = output
    } else if (typeof output !== 'undefined') {
      outputArguments = [output]
    }

    const returnCandidates = [
      message.returnValue,
      message.returnvalue,
      message.statusCode,
      message.statuscode,
      message.methodStatus,
      message.methodstatus
    ]
    const returnValue = returnCandidates.find(value => typeof value !== 'undefined')

    return {
      callStatus: message.callStatus,
      statusCode: message.statusCode,
      returnValue,
      outputArguments,
      rawPayload: payload
    }
  }

  _extractMethodFailure (payload) {
    const message = payload?.message ?? payload
    const candidates = [
      message?.exception,
      message?.error,
      message?.reason,
      message?.statusDescription,
      payload?.exception,
      payload?.error,
      payload?.reason,
      payload?.statusDescription
    ]
    const text = candidates.find(value => typeof value === 'string' && value.trim().length > 0)
    return text ? text.trim() : ''
  }

  _describeOutputArgument (argument, value, index) {
    return {
      index,
      name: argument?.Name || `Output ${index + 1}`,
      dataType: argument?.DataType?.Identifier ?? null,
      description: argument?.Description?.Text ?? argument?.Description?._text ?? '',
      value
    }
  }

  _describeReturnArgument (argument, value) {
    if (typeof value === 'undefined' || value === null) return null
    return {
      name: argument?.Name || 'Return value',
      dataType: argument?.DataType?.Identifier ?? null,
      description: argument?.Description?.Text ?? argument?.Description?._text ?? '',
      value
    }
  }

  buildMethodSchemaSection (methodData) {
    const inputArguments = Array.isArray(methodData?.arguments) ? methodData.arguments : []
    const outputArguments = Array.isArray(methodData?.outputArguments) ? methodData.outputArguments : []
    if (inputArguments.length === 0 && outputArguments.length === 0) return null

    const details = document.createElement('details')
    details.classList.add('methodSchemaCard')

    const summary = document.createElement('summary')
    summary.textContent = 'Method schema'
    details.appendChild(summary)

    const body = document.createElement('div')
    body.classList.add('methodSchemaBody')

    const appendArgumentSection = (title, argumentsList) => {
      const section = document.createElement('div')
      section.classList.add('methodSchemaSection')
      const heading = document.createElement('h4')
      heading.classList.add('methodSchemaTitle')
      heading.textContent = title
      section.appendChild(heading)

      if (argumentsList.length === 0) {
        const empty = document.createElement('p')
        empty.classList.add('methodHelpText')
        empty.textContent = 'None'
        section.appendChild(empty)
      } else {
        const list = document.createElement('ul')
        list.classList.add('methodSchemaList')
        for (const arg of argumentsList) {
          const item = document.createElement('li')
          const desc = arg?.Description?.Text ?? arg?.Description?._text ?? ''
          const arraySuffix = this._expectsArrayArgument(arg) ? '[]' : ''
          item.textContent = `${arg?.Name || 'Unnamed'}${arraySuffix}${desc ? ` — ${desc}` : ''}`
          list.appendChild(item)
        }
        section.appendChild(list)
      }

      body.appendChild(section)
    }

    appendArgumentSection('Inputs', inputArguments)
    appendArgumentSection('Outputs', outputArguments)
    details.appendChild(body)
    return details
  }

  _getJointPickerOptions () {
    const detected = this.methodState.detectedJoints
    return Array.isArray(detected) ? detected : []
  }

  _getJoiningProcessPickerOptions () {
    const detected = this.methodState.detectedJoiningProcesses
    return Array.isArray(detected) ? detected : []
  }

  _formatValueForDisplay (value, dataType) {
    if (value === null || typeof value === 'undefined') return '—'
    if (Array.isArray(value)) {
      const semantic = this._formatSemanticCollection(value)
      if (semantic) return semantic
      return `${value.length} item(s)\n${JSON.stringify(value, null, 2)}`
    }
    if (typeof value === 'boolean') return value ? 'True' : 'False'
    if (typeof value === 'string') return value
    if (typeof value === 'number') return String(value)
    if (dataType === 21 && value && typeof value === 'object') {
      const text = value.Text ?? value.text ?? value._text ?? ''
      const locale = value.Locale ?? value.locale ?? ''
      const renderedText = text === null || typeof text === 'undefined' || text === '' ? '—' : String(text)
      return locale ? `${renderedText} (${locale})` : renderedText
    }
    if (value?.pythonclass === 'LocalizedText') {
      return this._formatValueForDisplay(value, 21)
    }
    if (value?.pythonclass && value && typeof value === 'object') {
      const entries = Object.entries(value)
        .filter(([key]) => key !== 'pythonclass')
        .map(([key, entryValue]) => `${key}: ${this._formatValueForDisplay(entryValue, null)}`)
      if (entries.length > 0) {
        return `${value.pythonclass}\n${entries.join('\n')}`
      }
    }
    if (value && typeof value === 'object') return JSON.stringify(value, null, 2)
    return String(value)
  }

  _formatSemanticCollection (items) {
    if (!Array.isArray(items) || items.length === 0) return ''
    const first = items[0]?.Value ?? items[0]
    if (first?.JointId || first?.Id || first?.JointMetaData) {
      const labels = items
        .map(item => item?.Value?.JointId ?? item?.JointId ?? item?.Value?.Id ?? item?.Id ?? '')
        .filter(Boolean)
      return `Joint list (${labels.length})\n${labels.join('\n')}`
    }
    if (first?.JoiningProcessId || first?.ProgramId || first?.JoiningProcessMetaData) {
      const labels = items
        .map(item => item?.Value?.SelectionName ?? item?.SelectionName ?? item?.Value?.JoiningProcessId ?? item?.JoiningProcessId ?? item?.Value?.ProgramId ?? item?.ProgramId ?? '')
        .filter(Boolean)
      return `Joining processes (${labels.length})\n${labels.join('\n')}`
    }
    if (first?.EntityId || first?.Description) {
      const labels = items
        .map(item => item?.EntityId ?? item?.Value?.EntityId ?? item?.Description ?? item?.Value?.Description ?? '')
        .filter(Boolean)
      return `Associated entities (${labels.length})\n${labels.join('\n')}`
    }
    return ''
  }

  _createDefinitionRow (label, value, description = '') {
    const row = document.createElement('div')
    row.classList.add('methodResultRow')

    const term = document.createElement('dt')
    term.classList.add('methodResultTerm')
    term.textContent = label
    row.appendChild(term)

    const detail = document.createElement('dd')
    detail.classList.add('methodResultDetail')
    const valueBlock = document.createElement('pre')
    valueBlock.classList.add('methodResultValue')
    valueBlock.textContent = value
    detail.appendChild(valueBlock)

    if (description) {
      const descriptionNode = document.createElement('p')
      descriptionNode.classList.add('methodResultDescription')
      descriptionNode.textContent = description
      detail.appendChild(descriptionNode)
    }

    row.append(term, detail)
    return row
  }

  _renderStructuredResultSections (summary, value, labelPrefix = '') {
    if (value?.pythonclass === 'LocalizedText') return false
    if (!value || typeof value !== 'object' || Array.isArray(value)) return false
    const entries = Object.entries(value).filter(([key]) => key !== 'pythonclass')
    if (entries.length === 0) return false
    for (const [key, nestedValue] of entries) {
      summary.appendChild(
        this._createDefinitionRow(
          labelPrefix ? `${labelPrefix} — ${key}` : key,
          this._formatValueForDisplay(nestedValue, null)
        )
      )
    }
    return true
  }

  buildMethodResultView (methodName, payload, methodData = {}) {
    const extracted = this._extractMethodResponse(payload, methodData)
    const failureText = this._extractMethodFailure(payload)
    const declaredOutputArguments = Array.isArray(methodData?.outputArguments) ? methodData.outputArguments : []
    const declaredReturnArgument = methodData?.returnArgument
    const structuredOutputArguments = extracted.outputArguments.map((value, index) =>
      this._describeOutputArgument(declaredOutputArguments[index], value, index)
    )
    const structuredReturnArgument = this._describeReturnArgument(declaredReturnArgument, extracted.returnValue)
    const result = {
      method: methodName,
      timestamp: new Date().toISOString(),
      returnValue: structuredReturnArgument,
      outputArguments: structuredOutputArguments,
      payload: extracted.rawPayload
    }

    const card = document.createElement('section')
    card.classList.add('methodResultCard')

    const title = document.createElement('h3')
    title.classList.add('methodResultTitle')
    title.textContent = methodName
    card.appendChild(title)

    const timestamp = document.createElement('p')
    timestamp.classList.add('methodResultTimestamp')
    timestamp.textContent = new Date(result.timestamp).toLocaleString()
    card.appendChild(timestamp)

    const summary = document.createElement('dl')
    summary.classList.add('methodResultList')
    if (failureText) {
      summary.appendChild(this._createDefinitionRow('Call status', extracted.callStatus || 'Failed', failureText))
    }
    if (result.returnValue) {
      summary.appendChild(this._createDefinitionRow(
        result.returnValue.name,
        this._formatValueForDisplay(result.returnValue.value, result.returnValue.dataType),
        result.returnValue.description
      ))
    }

    if (structuredOutputArguments.length > 0) {
      for (const outputArgument of structuredOutputArguments) {
        summary.appendChild(
          this._createDefinitionRow(
            outputArgument.name,
            this._formatValueForDisplay(outputArgument.value, outputArgument.dataType),
            outputArgument.description
          )
        )
        this._renderStructuredResultSections(summary, outputArgument.value, outputArgument.name)
      }
    } else {
      const noOutputText = failureText
        ? 'Unavailable because the method call failed'
        : 'No output arguments'
      summary.appendChild(this._createDefinitionRow('Output arguments', noOutputText))
    }

    card.appendChild(summary)

    const rawDetails = document.createElement('details')
    rawDetails.classList.add('methodResultDebug')
    const rawSummary = document.createElement('summary')
    rawSummary.textContent = 'Raw payload'
    rawDetails.appendChild(rawSummary)
    const rawPayload = document.createElement('pre')
    rawPayload.classList.add('methodResultValue')
    rawPayload.textContent = JSON.stringify(result.payload, null, 2)
    rawDetails.appendChild(rawPayload)
    card.appendChild(rawDetails)

    return card
  }

  formatMethodResult (methodName, payload, methodData = {}) {
    return this.buildMethodResultView(methodName, payload, methodData)
  }

  /**
   * Create an input field that helps in the invocation of a method
   * @param {*} arg the argument that you want the data for
   * @param {*} area the area where the input field should go
   * @param {*} defaultValue optional pre-filled value
   * @param {*} callback optional onchange callback
   * @returns a function that returns {value, type} when called
   */
  createMethodInput (arg, area, defaultValue = '', callback, methodName = '', argumentIndex = 0, metadataDefault, context = {}) {
    const dataTypeId = String(arg?.DataType?.Identifier ?? '')
    const normalizedArgumentName = String(arg?.Name ?? '').replace(/[^a-z0-9]/gi, '').toLowerCase()
    const resolvedMetadataDefault = this.resolveMetadataDefault(metadataDefault)
    if ((defaultValue === '' || typeof defaultValue === 'undefined') && typeof resolvedMetadataDefault !== 'undefined') {
      defaultValue = resolvedMetadataDefault
    }
    if ((defaultValue === '' || typeof defaultValue === 'undefined') && this._isProductInstanceUriArgument(arg)) {
      const allowEmpty = ['getjointlist', 'getjoiningprocesslist'].includes(this._normalizeArgumentName(methodName))
      const liveToolDefault = this.resolveMetadataDefault({ source: 'productid', allowEmpty })
      defaultValue = liveToolDefault
    }
    defaultValue = this._applyNamedDefaults(arg, defaultValue, methodName, argumentIndex)

    // Argument label
    if (arg.Name && arg.Name.length > 0) {
      const titleLabel = this.screen.createLabel(`${arg.Name}  `)
      titleLabel.classList.add('methodLabel')
      area.appendChild(titleLabel)
    }

    const descText = arg?.Description?.Text ?? arg?.Description?._text ?? ''
    const inputSource = this._resolveInputSource(arg, defaultValue, metadataDefault, context?.profile)
    this._createInputSourceHint(this._formatInputSource(inputSource), area)

    const structureEditor = this._createGenericStructureEditor(arg, area, defaultValue, descText)
    if (structureEditor) {
      return structureEditor
    }

    if (this._expectsArrayArgument(arg) && this._isStringLikeArgument(arg)) {
      const wrapper = document.createElement('div')
      wrapper.classList.add('methodInputRight', 'methodCompositeInput', 'methodArrayInput')
      area.appendChild(wrapper)

      const list = document.createElement('div')
      list.classList.add('methodArrayList')
      wrapper.appendChild(list)

      const initialValues = Array.isArray(defaultValue)
        ? defaultValue.map(value => String(value ?? ''))
        : (String(defaultValue ?? '').trim() ? [String(defaultValue).trim()] : [])
      const items = [...initialValues]

      const renderItems = () => {
        list.replaceChildren()
        if (items.length === 0) {
          const emptyHint = document.createElement('p')
          emptyHint.classList.add('methodHelpText')
          emptyHint.textContent = 'Empty array will be sent.'
          list.appendChild(emptyHint)
          return
        }
        items.forEach((itemValue, itemIndex) => {
          const row = document.createElement('div')
          row.classList.add('methodArrayRow')
          const input = this.screen.createInput(itemValue, row, (value) => {
            items[itemIndex] = value
            if (callback) callback(items)
          }, 70)
          input.dataType = arg.DataType
          input.title = `Datatype: ${arg?.DataType?.Name || 'String'}[]\n${descText}`
          const removeButton = this.screen.createButton('Remove', row, () => {
            items.splice(itemIndex, 1)
            renderItems()
            if (callback) callback(items)
          })
          removeButton.classList.add?.('methodArrayButton')
          list.appendChild(row)
        })
      }

      const controls = document.createElement('div')
      controls.classList.add('methodArrayControls')
      this.screen.createButton('Add item', controls, () => {
        items.push('')
        renderItems()
      })
      wrapper.appendChild(controls)
      renderItems()

      return function () {
        return {
          value: items
            .map(value => String(value ?? '').trim())
            .filter(value => value.length > 0),
          type: arg.DataType
        }
      }
    }

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
        selectionArea.classList.add('methodInputRight', 'methodCompositeInput', 'joiningProcessIdInput')
        area.appendChild(selectionArea)

        const modeLabel = this.screen.createLabel('Lookup mode')
        modeLabel.classList.add('methodLabel', 'methodSubLabel')
        selectionArea.appendChild(modeLabel)

        const drop = this.screen.createDropdown('', () => {
          saveMethodPreferences(context.methodStorageKey, {
            ...context.storedPreferences,
            joiningProcessLookupMode: drop.select.value
          })
          applyModePresentation()
        }, 'dropJoiningProcess')
        drop.classList.add('methodDropdownWrap')
        for (const mode of JOINING_PROCESS_IDENTIFICATION_MODES) {
          drop.addOption(mode.label, mode.index)
        }
        selectionArea.appendChild(drop)

        const valueLabel = this.screen.createLabel('Identifier value')
        valueLabel.classList.add('methodLabel', 'methodSubLabel')
        selectionArea.appendChild(valueLabel)

        const sel = this.screen.createInput('', selectionArea, callback, 55)
        sel.dataType = arg.DataType
        sel.title = `Datatype: JoiningProcessId\n${descText}`
        sel.value = ''
        selectionArea.appendChild(sel)

        const helper = document.createElement('p')
        helper.classList.add('methodHelpText')
        selectionArea.appendChild(helper)

        const joiningProcessOptions = this._getJoiningProcessPickerOptions()
        if (joiningProcessOptions.length > 0) {
          const pickerLabel = this.screen.createLabel('Discovered processes')
          pickerLabel.classList.add('methodLabel', 'methodSubLabel')
          selectionArea.appendChild(pickerLabel)

          const picker = this.screen.createDropdown('', () => {
            const selected = joiningProcessOptions.find(option =>
              `${option.joiningProcessId}|${option.joiningProcessOriginId}|${option.selectionName}` === String(picker.select.value)
            )
            if (selected) {
              const selectedMode = Number.parseInt(drop.select.value, 10)
              sel.value = selectedMode === 1
                ? selected.joiningProcessOriginId
                : selectedMode === 2
                  ? selected.selectionName
                  : selected.joiningProcessId
            }
          })
          picker.classList.add('methodDropdownWrap')
          picker.select.setAttribute?.('aria-label', 'Discovered joining processes')
          picker.addOption('Choose discovered joining process', '')
          for (const option of joiningProcessOptions) {
            const label = option.selectionName || option.joiningProcessId || option.joiningProcessOriginId
            picker.addOption(
              `${label} — Id: ${option.joiningProcessId || '-'} / Origin: ${option.joiningProcessOriginId || '-'}`,
              `${option.joiningProcessId}|${option.joiningProcessOriginId}|${option.selectionName}`
            )
          }
          selectionArea.appendChild(picker)
        }

        const applyModePresentation = () => {
          const mode = JOINING_PROCESS_IDENTIFICATION_MODES.find(candidate => String(candidate.index) === String(drop.select.value)) ||
            JOINING_PROCESS_IDENTIFICATION_MODES[0]
          sel.placeholder = mode.placeholder
          helper.textContent = mode.help
        }

        drop.select.value = String(context.storedPreferences?.joiningProcessLookupMode ?? JOINING_PROCESS_IDENTIFICATION_MODES[0].index)
        applyModePresentation()

        return function () {
          const value = []
          for (const mode of JOINING_PROCESS_IDENTIFICATION_MODES) {
            value.push(parseInt(drop.select.value) === mode.index
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
        if (this._isJointIdArgument(arg)) {
          const wrapper = document.createElement('div')
          wrapper.classList.add('methodInputRight', 'methodCompositeInput')
          const input12 = this.screen.createInput('', wrapper, callback, 45)
          input12.dataType = arg.DataType
          input12.title = `Datatype: String\n${descText}`
          input12.value = defaultValue

          const jointOptions = this._getJointPickerOptions(context.methodData)
          if (jointOptions.length > 0) {
            const picker = this.screen.createDropdown('', () => {
              input12.value = String(picker.select.value || '')
            })
            picker.classList.add('methodDropdownWrap')
            picker.select.setAttribute?.('aria-label', 'Discovered joints')
            picker.addOption('Choose discovered joint', '')
            for (const jointId of jointOptions) {
              picker.addOption(jointId, jointId)
            }
            wrapper.appendChild(picker)
          }

          area.appendChild(wrapper)
          return function () { return { value: input12.value, type: input12.dataType } }
        }
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
