const METHOD_NODE_CLASS = 4 // OPC UA NodeClass for Method nodes
import { ijtLog } from '../ijt-logger.mjs'

const INTEGER_DATA_TYPE_IDS = new Set([2, 3, 4, 5, 6, 7, 8, 9])
const FLOAT_DATA_TYPE_IDS = new Set([10, 11])
const STRING_DATA_TYPE_IDS = new Set([12, 31918])
const BUILTIN_OR_ALIAS_DATA_TYPE_IDS = new Set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 21, 290, 294, 31918])

function castScalarInputValue (dataTypeId, value) {
  if (INTEGER_DATA_TYPE_IDS.has(dataTypeId)) {
    return Number.parseInt(value, 10)
  }
  if (FLOAT_DATA_TYPE_IDS.has(dataTypeId)) {
    return Number.parseFloat(value)
  }
  if (STRING_DATA_TYPE_IDS.has(dataTypeId) || dataTypeId === 13) {
    return String(value ?? '')
  }
  if (dataTypeId === 1) {
    return value === true || value === 'true'
  }
  return value
}

function castInputValue (dataTypeId, value, valueRank) {
  const allowsArray = valueRank >= 0 || valueRank === -2 || valueRank === -3
  const requiresArray = valueRank >= 0

  if (allowsArray && Array.isArray(value)) {
    return value.map(item => castScalarInputValue(dataTypeId, item))
  }
  if (requiresArray) {
    return value === '' || value == null
      ? []
      : [castScalarInputValue(dataTypeId, value)]
  }
  return castScalarInputValue(dataTypeId, value)
}

function isStructureFieldEntry (entry) {
  return entry && typeof entry === 'object' && Object.hasOwn(entry, 'name') && Object.hasOwn(entry, 'value')
}

function isWrappedStructureEntry (entry) {
  return entry && typeof entry === 'object' && Array.isArray(entry.value)
}

function isCustomStructureTypeId (typeId) {
  return Number.isInteger(typeId) && !BUILTIN_OR_ALIAS_DATA_TYPE_IDS.has(typeId)
}

function normalizeSchemaArgument (argument = {}) {
  return {
    ...argument,
    Name: argument?.Name || '',
    DataType: argument?.DataType || {},
    ValueRank: argument?.ValueRank ?? -1,
    ArrayDimensions: argument?.ArrayDimensions ?? null,
    Description: argument?.Description || null,
    FieldDefinitions: Array.isArray(argument?.FieldDefinitions) ? argument.FieldDefinitions : []
  }
}

const COMPATIBILITY_GROUPS = Object.freeze({
  SendSimulatedBulkResults: {
    id: 'simulate-results',
    label: 'Simulate Results',
    description: 'Simulate joining results.',
    parentId: 'simulations',
    parentLabel: 'Simulations',
    parentDescription: 'Simulation methods.'
  }
})

const COMPATIBILITY_METHOD_DEFAULTS = Object.freeze({
  RequestResults: {
    argumentDefaults: {
      FromSequenceNumber: 0,
      ToSequenceNumber: 0,
      FromTime: '2000-01-01T00:00:00Z',
      ToTime: '9999-01-01T00:00:00Z',
      RequestedMinimumDurationBetweenResults: 0
    }
  }
})

export class MethodManager {
  constructor (addressSpace) {
    this.addressSpace = addressSpace
    this.methodObject = {}
    this.methodMetadata = { groups: [], defaults: { byName: {}, byPath: {} }, globalDefaults: {} }
  }

  /**
   * This function takes a list of folders and search them for methods. Then getMethodNames(), getMethod(), and call() can be used to invoke them
   * @param {*} methodFolders a list of folders that should be searched for methods
   * @returns a Promise to load the methods in the list
   */
  async setupMethodsInFolders (methodFolders) {
    this.tighteningSystemNode = await this.addressSpace.addressSpacePromise()
    this.methodObject = {}
    const methodPromises = methodFolders.map(async (folderPath) => {
      try {
        await this.addressFolder(JSON.stringify(folderPath))
      } catch (error) {
        ijtLog.warn('Skipping unavailable method folder', folderPath, error)
      }
    })
    await Promise.all(methodPromises)
    this.addressSpace.connectionManager.trigger(this.addressSpace.connectionManager.CONNECTION_STATES.METHODS, true)
  }

  /**
   * Support function that ensures that the containing folder is loaded
   * @param {*} folderPath the path to the folder. Remember to add the namespace number
   * @returns a Promise to setup all methods in a folder
   */
  async addressFolder (folderPath) {
    if (!folderPath || folderPath === '') {
      return this.folderPromise(this.tighteningSystemNode) // Automatically add all methods in the top folder (if path is empty)
    } else {
      const folderNode = await this.addressSpace.findNodeFromPathPromise(folderPath)
      return this.folderPromise(folderNode)
    }
  }

  /**
   * Promise to set up a folder with all the method nodes.
   * @param {*} folderNode the node that contains methods
   * @returns  a Promise to setup all methods in a folder
   */
  async folderPromise (folderNode) {
    const methodPromises = []
    const relations = folderNode.getChildRelations('component')
    const children = await this.addressSpace.relationsToNodes(relations)
    for (const child of children) {
      if (parseInt(child.nodeClass) === METHOD_NODE_CLASS) {
        methodPromises.push(this.setupMethod(child))
      }
    }
    const methodList = await Promise.all(methodPromises)
    for (const methodItem of methodList) {
      const pathText = String(methodItem.methodNode?.nodeIdString || methodItem.methodNode?.nodeId || '')
      this.methodObject[methodItem.methodNode.displayName] = {
        parentNode: folderNode,
        methodNode: methodItem.methodNode,
        arguments: methodItem.arguments.map(normalizeSchemaArgument),
        outputArguments: methodItem.outputArguments.map(normalizeSchemaArgument),
        returnArgument: methodItem.returnArgument ? normalizeSchemaArgument(methodItem.returnArgument) : undefined,
        nodeIdString: pathText,
        metadata: this._buildMethodPresentation(pathText, methodItem.methodNode.displayName)
      }
    }
  }

  setMethodMetadata (metadata = {}) {
    this.methodMetadata = {
      groups: Array.isArray(metadata.groups) ? metadata.groups : [],
      defaults: {
        byName: metadata?.defaults?.byName || {},
        byPath: metadata?.defaults?.byPath || {}
      },
      globalDefaults: metadata?.globalDefaults || {}
    }
    for (const [name, methodData] of Object.entries(this.methodObject || {})) {
      const pathText = methodData.nodeIdString || methodData.methodNode?.nodeIdString || methodData.methodNode?.nodeId || ''
      methodData.metadata = this._buildMethodPresentation(pathText, name)
    }
  }

  _normalizeMethodPath (pathText = '') {
    return String(pathText)
      .replace(/^ns=\d+;s=/, '')
      .trim()
  }

  _buildMethodPresentation (pathText, displayName) {
    const normalizedPath = this._normalizeMethodPath(pathText)
    const byName = this.methodMetadata?.defaults?.byName?.[displayName] || {}
    const byPath = this.methodMetadata?.defaults?.byPath?.[normalizedPath] || {}
    const groups = Array.isArray(this.methodMetadata?.groups) ? this.methodMetadata.groups : []
    const compatibilityGroup = COMPATIBILITY_GROUPS[displayName]
    const compatibilityDefaults = COMPATIBILITY_METHOD_DEFAULTS[displayName] || {}
    const explicitGroupId = byPath?.groupId || byName?.groupId || compatibilityGroup?.id
    const group = groups.find(candidate => candidate?.id === explicitGroupId) ||
      groups
        .flatMap(candidate => (Array.isArray(candidate?.paths) ? candidate.paths : [])
          .filter(prefix => normalizedPath.startsWith(prefix))
          .map(prefix => ({ candidate, prefix })))
        .sort((left, right) => right.prefix.length - left.prefix.length)[0]?.candidate ||
      null
    return {
      path: normalizedPath,
      groupId: group?.id || explicitGroupId || 'other-methods',
      groupLabel: group?.label || compatibilityGroup?.label || 'Additional Methods',
      groupDescription: group?.description || compatibilityGroup?.description || '',
      parentId: group?.parentId || compatibilityGroup?.parentId || null,
      parentLabel: compatibilityGroup?.parentLabel || '',
      parentDescription: compatibilityGroup?.parentDescription || '',
      defaults: {
        ...(compatibilityDefaults.argumentDefaults || {}),
        ...(byName.argumentDefaults || {}),
        ...(byPath.argumentDefaults || {})
      },
      notes: [...(compatibilityDefaults.notes || []), ...(byName.notes || []), ...(byPath.notes || [])]
    }
  }

  getGroupedMethods () {
    const groups = new Map()
    const definitions = new Map()
    for (const definition of this.methodMetadata.groups) {
      definitions.set(definition.id, definition)
    }
    for (const definition of this.methodMetadata.groups) {
      groups.set(definition.id, {
        id: definition.id,
        label: definition.label,
        description: definition.description || '',
        parentId: definition.parentId || null,
        parentLabel: definitions.get(definition.parentId)?.label || '',
        parentDescription: definitions.get(definition.parentId)?.description || '',
        methods: []
      })
    }
    for (const [name, methodData] of Object.entries(this.methodObject || {})) {
      const metadata = methodData.metadata || this._buildMethodPresentation(methodData.nodeIdString, name)
      const groupId = metadata.groupId || 'other-methods'
      if (!groups.has(groupId)) {
        groups.set(groupId, {
          id: groupId,
          label: metadata.groupLabel || 'Additional Methods',
          description: metadata.groupDescription || '',
          parentId: metadata.parentId || null,
          parentLabel: metadata.parentLabel || '',
          parentDescription: metadata.parentDescription || '',
          methods: []
        })
      }
      groups.get(groupId).methods.push({ name, methodData })
    }
    return [...groups.values()]
      .filter(group => group.methods.length > 0)
      .map(group => ({
        ...group,
        methods: group.methods.sort((a, b) => a.name.localeCompare(b.name))
      }))
  }

  /**
   * Given a method node, set it up and sort out the data so that it becomes
   * easy to invoke (using the InputArguments / OutputArguments children).
   * @param {object} methodNode
   * @returns {Promise<{methodNode: object, arguments: object[], outputArguments: object[], returnArgument?: object}>}
   */
  async setupMethod (methodNode) {
    const childRelations = [
      ...methodNode.getChildRelations('hasProperty'),
      ...methodNode.getChildRelations('component')
    ]
    const uniqueRelations = childRelations.filter((relation, index, relations) =>
      index === relations.findIndex(candidate => candidate?.NodeId === relation?.NodeId)
    )
    const inputArguments = uniqueRelations.find(
      x => x.BrowseName.Name === 'InputArguments')
    const outputArguments = uniqueRelations.find(
      x => x.BrowseName.Name === 'OutputArguments')
    const returnValue = uniqueRelations.find(
      x => x.BrowseName.Name === 'ReturnValue')

    const inputArgumentsNode = inputArguments
      ? await this.addressSpace.relationsToNodes([inputArguments])
      : []
    const outputArgumentsNode = outputArguments
      ? await this.addressSpace.relationsToNodes([outputArguments])
      : []
    const returnValueNode = returnValue
      ? await this.addressSpace.relationsToNodes([returnValue])
      : []

    const simplifiedArguments = []
    for (const arg of inputArgumentsNode) {
      for (const argContent of arg.data.attributes.Value) {
        if (argContent) {
          simplifiedArguments.push(normalizeSchemaArgument(argContent))
        } else {
          ijtLog.warn('Method arguments could not be found:', arg?.data?.value)
        }
      }
    }

    const simplifiedOutputArguments = []
    for (const arg of outputArgumentsNode) {
      for (const argContent of arg.data.attributes.Value) {
        if (argContent) {
          simplifiedOutputArguments.push(normalizeSchemaArgument(argContent))
        } else {
          ijtLog.warn('Method output arguments could not be found:', arg?.data?.value)
        }
      }
    }

    let simplifiedReturnArgument
    for (const arg of returnValueNode) {
      const returnDefinition = arg?.data?.attributes?.Value?.[0]
      if (returnDefinition) {
        simplifiedReturnArgument = normalizeSchemaArgument(returnDefinition)
        break
      }
    }

    return {
      methodNode,
      arguments: simplifiedArguments,
      outputArguments: simplifiedOutputArguments,
      returnArgument: simplifiedReturnArgument,
      argumentMetadata: simplifiedArguments.map(arg => ({
        valueRank: arg?.ValueRank,
        arrayDimensions: arg?.ArrayDimensions,
        fieldDefinitions: arg?.FieldDefinitions
      }))
    }
  }

  /**
   * Return a list of Method names
   * @returns
   */
  getMethodNames () {
    return Object.keys(this.methodObject || {})
  }

  /**
   * Given a method name, return data about the method
   * @param {*} name the name of the method
   * @returns
   */
  getMethod (name) {
    return this.methodObject?.[name]
  }

  /**
   * Invokes a method
   * @param {*} methodNode the method Node
   * @param {*} inputs the argument data
   */
  async call (methodData, inputs) {
    const inputArguments = []
    for (const [index, row] of inputs.entries()) {
      const argumentDefinition = methodData.arguments?.[index]
      const valueRank = Number(argumentDefinition?.ValueRank)
      const schemaTypeId = Number(argumentDefinition?.DataType?.Identifier)
      const rowTypeId = Number(row.type.Identifier)
      const dataTypeId = Number.isInteger(schemaTypeId) ? schemaTypeId : rowTypeId
      const castValue = castInputValue(dataTypeId, row.value, valueRank)
      const dataTypeNamespaceIndex = Number(argumentDefinition?.DataType?.NamespaceIndex ?? row.type?.NamespaceIndex)
      const dataTypeName = String(argumentDefinition?.DataType?.Name || row?.structure || '').trim()
      const hasStructureFieldEntries = Array.isArray(row?.value) && row.value.every(isStructureFieldEntry)
      const hasWrappedStructureEntries = Array.isArray(row?.value) && row.value.every(isWrappedStructureEntry)
      const shouldPreserveStructureEnvelope = isCustomStructureTypeId(dataTypeId)
      let value = castValue
      if (shouldPreserveStructureEnvelope && hasStructureFieldEntries) {
        value = {
          ...(row?.structure ? { structure: row.structure } : {}),
          value: row.value
        }
      } else if (shouldPreserveStructureEnvelope && hasWrappedStructureEntries) {
        value = row.value.map(entry => ({
          ...(entry?.structure ? { structure: entry.structure } : {}),
          value: entry.value
        }))
      }

      const payload = {
        dataType: dataTypeId,
        value
      }
      if (Number.isInteger(dataTypeNamespaceIndex)) {
        payload.dataTypeNamespaceIndex = dataTypeNamespaceIndex
      }
      if (dataTypeName) {
        payload.dataTypeName = dataTypeName
      }
      inputArguments.push(payload)
    }

    return this.addressSpace.methodCall(methodData.parentNode.nodeId, methodData.methodNode.nodeId, inputArguments)
  }
}
