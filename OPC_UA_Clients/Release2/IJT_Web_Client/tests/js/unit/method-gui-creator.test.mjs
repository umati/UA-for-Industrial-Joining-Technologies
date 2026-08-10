import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import MethodGUICreator from '../../../src/javascripts/views/methods/method-gui-creator.mjs'

function makeCreator () {
  return new MethodGUICreator({
    createLabel: (text = '') => ({ classList: makeClassList(), textContent: text })
  }, {}, {}, {})
}

function makeArg (name, dataType = 7) {
  return {
    Name: name,
    DataType: { Identifier: dataType },
  }
}

function makeClassList () {
  return { add () {} }
}

function makeContainer () {
  return {
    children: [],
    classList: makeClassList(),
    appendChild (child) {
      this.children.push(child)
    }
  }
}

function makeElement (tagName) {
  return {
    tagName,
    children: [],
    classList: makeClassList(),
    appendChild (child) {
      this.children.push(child)
    },
    append (...children) {
      this.children.push(...children)
    },
    set textContent (value) {
      this._textContent = value
    },
    get textContent () {
      return this._textContent
    }
  }
}

function makeScreenStub () {
  return {
    createLabel: (text = '') => ({ classList: makeClassList(), textContent: text }),
    createDropdown: () => {
      const options = []
      return {
        classList: makeClassList(),
        select: { value: '' },
        addOption: (label, value) => options.push({ label, value }),
        get value () { return this.select.value },
        options
      }
    },
    createInput: (_value, area) => {
      const input = {
        value: '',
        placeholder: '',
        title: '',
        classList: makeClassList()
      }
      area.appendChild(input)
      return input
    }
  }
}

function makeInputCreator () {
  const screen = makeScreenStub()
  const area = makeContainer()
  return { creator: new MethodGUICreator(screen, {}, {}, {}), area }
}

beforeEach(() => {
  vi.stubGlobal('document', {
    createElement: (tagName) => makeElement(tagName)
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('MethodGUICreator default arguments', () => {
  it('keeps explicit configured defaults', () => {
    const creator = makeCreator()

    const value = creator._applyNamedDefaults(makeArg('Event Type'), 42, 'SimulateEvents', 0)

    expect(value).toBe(42)
  })

  it('defaults SimulateEvents event type to a valid representative event', () => {
    const creator = makeCreator()

    const value = creator._applyNamedDefaults(makeArg('Event Type'), '', 'SimulateEvents', 0)

    expect(value).toBe(1)
  })

  it('defaults SimulateConditions event type to the same representative event', () => {
    const creator = makeCreator()

    const value = creator._applyNamedDefaults(makeArg('Event Type'), '', 'SimulateConditions', 0)

    expect(value).toBe(1)
  })

  it('defaults SimulateBulkEvents event type and count', () => {
    const creator = makeCreator()

    const eventType = creator._applyNamedDefaults(makeArg('Event Type'), '', 'SimulateBulkEvents', 0)
    const count = creator._applyNamedDefaults(makeArg('Count'), '', 'SimulateBulkEvents', 1)

    expect(eventType).toBe(1)
    expect(count).toBe(3)
  })

  it('defaults batch or sync classification to BATCH', () => {
    const creator = makeCreator()

    const value = creator._applyNamedDefaults(makeArg('Classification', 3), '', 'SimulateBatch_Or_Sync_Result', 0)

    expect(value).toBe(3)
  })

  it('normalizes metadata argument names before applying a recommended default', () => {
    const creator = makeCreator()

    const value = creator.getMetadataDefault(
      { Classification: 3 },
      'Result Classification'
    )

    expect(value).toBe(3)
  })

  it('fills otherwise unspecified numeric inputs with the configured safe fallback', () => {
    const creator = new MethodGUICreator(
      {},
      { methodMetadata: { globalDefaults: { integerFallback: 1 } } },
      {},
      {}
    )

    const value = creator._applyNamedDefaults(makeArg('Unspecified Count'), '', 'AnyMethod', 0)

    expect(value).toBe(1)
  })

  it('fills otherwise unspecified string inputs with an editable sample', () => {
    const creator = new MethodGUICreator(
      {},
      { methodMetadata: { globalDefaults: { stringFallback: 'Sample' } } },
      {},
      {}
    )

    const value = creator._applyNamedDefaults(makeArg('Description', 12), '', 'AnyMethod', 0)

    expect(value).toBe('Sample')
  })

  it('fills every ProductInstanceUri argument from the discovered Tool URI', () => {
    const creator = new MethodGUICreator(
      {},
      {},
      {},
      {},
      { productInstanceUri: 'urn:server:tool:1' }
    )

    const value = creator._applyNamedDefaults(makeArg('ProductInstanceUri', 12), '', 'AnyMethod', 0)

    expect(value).toBe('urn:server:tool:1')
  })

  it('keeps the classification dropdown and selected default for Result Classification', () => {
    const { creator, area } = makeInputCreator()

    const grabValue = creator.createMethodInput(
      makeArg('Result Classification', 3),
      area,
      3
    )

    const dropdown = area.children.find(child => Array.isArray(child?.options))
    expect(dropdown.options).toEqual([
      { label: 'BATCH (3)', value: 3 },
      { label: 'SYNC (2)', value: 2 }
    ])
    expect(dropdown.select.value).toBe('3')
    expect(grabValue().value).toBe(3)
  })

  it('returns empty ProductInstanceUri when no live tool was discovered', () => {
    const creator = new MethodGUICreator({}, {}, {}, { productId: 'urn:test:tool:1' })

    const value = creator.resolveMetadataDefault({ source: 'productid', allowEmpty: false })

    expect(value).toBe('')
  })

  it('prefers the server-discovered Tool.ProductInstanceUri over Settings fallback', () => {
    const creator = new MethodGUICreator(
      {},
      {},
      {},
      { productId: 'urn:settings:tool:1' },
      { productInstanceUri: 'urn:server:tool:2' }
    )

    const value = creator.resolveMetadataDefault({ source: 'productid', allowEmpty: false })

    expect(value).toBe('urn:server:tool:2')
  })

  it('isolates live method defaults for clients that share user settings', () => {
    const sharedSettings = { methodDefaults: {} }
    const local = new MethodGUICreator({}, {}, {}, sharedSettings, {
      productInstanceUri: 'urn:local:tool',
      detectedTools: [],
      detectedJoints: [],
      detectedJoiningProcesses: []
    })
    const pf8 = new MethodGUICreator({}, {}, {}, sharedSettings, {
      productInstanceUri: 'urn:pf8:tool',
      detectedTools: [],
      detectedJoints: [],
      detectedJoiningProcesses: []
    })

    expect(local.resolveMetadataDefault({ source: 'productid' })).toBe('urn:local:tool')
    expect(pf8.resolveMetadataDefault({ source: 'productid' })).toBe('urn:pf8:tool')
    expect(local.methodState).not.toBe(pf8.methodState)
    expect(local.settings).toBe(pf8.settings)
  })

  it('ignores saved ProductInstanceUri values so live discovery stays authoritative', () => {
    const creator = new MethodGUICreator({}, {}, {}, {
      productId: 'www.atlascopco.com/53F22F10-B313-4B1D-924C-3A3EC7FCA002'
    })

    const value = creator.getSavedArgumentValue(
      { type: { Identifier: 12 }, value: 'www.atlascopco.com/53F22F10-B313-4B1D-924C-3A3EC7FCA002' },
      makeArg('ProductInstanceUri', 12)
    )

    expect(value).toBeUndefined()
  })

  it('restores saved array values for true array arguments', () => {
    const creator = makeCreator()

    const value = creator.getSavedArgumentValue(
      { type: { Identifier: 12 }, value: ['IdA', 'IdB'] },
      { Name: 'IdentifierFilter', DataType: { Identifier: 12 }, ValueRank: 1 }
    )

    expect(value).toEqual(['IdA', 'IdB'])
  })

  it('ignores stale scalar saved values for true array arguments', () => {
    const creator = makeCreator()

    const value = creator.getSavedArgumentValue(
      { type: { Identifier: 12 }, value: '{' },
      { Name: 'IdentifierNames', DataType: { Identifier: 12 }, ValueRank: 1 }
    )

    expect(value).toBeUndefined()
  })

  it('treats ProductInstanceUri as a generic schema-driven default without per-method metadata', () => {
    const creator = new MethodGUICreator(
      makeScreenStub(),
      {},
      {},
      {},
      { productInstanceUri: 'urn:server:tool:generic' }
    )

    const value = creator.createMethodInput(
      makeArg('ProductInstanceUri', 12),
      makeContainer(),
      '',
      undefined,
      'AnyFutureMethod',
      0,
      undefined
    )().value

    expect(value).toBe('urn:server:tool:generic')
  })

  it('resolves current UTC defaults for SetTime', () => {
    const creator = makeCreator()

    const value = creator.resolveMetadataDefault({ source: 'currentUtc' })

    expect(Number.isNaN(Date.parse(value))).toBe(false)
    expect(value).toMatch(/Z$/)
  })

  it('formats method results with method name and indented payload', () => {
    const creator = makeCreator()

    const result = creator.formatMethodResult('GetJointList', { output: [1, 2, 3] }, {
      outputArguments: [
        { Name: 'Joints', DataType: { Identifier: 3011 } },
        { Name: 'Count', DataType: { Identifier: 7 } },
        { Name: 'MoreData', DataType: { Identifier: 1 } }
      ]
    })

    expect(result.tagName).toBe('section')
    expect(result.children[0].textContent).toBe('GetJointList')
  })

  it('surfaces return value and output arguments from websocket method responses', () => {
    const creator = makeCreator()

    const result = creator.formatMethodResult('EnableAsset', {
      message: {
        returnValue: { code: 0, name: 'OK_SUCCESS' },
        output: [
          { Status: 0 },
          { StatusMessage: 'Asset enabled' }
        ]
      }
    }, {
      outputArguments: [
        { Name: 'Status', DataType: { Identifier: 6 } },
        { Name: 'StatusMessage', DataType: { Identifier: 12 } }
      ]
    })

    const outputList = result.children[2]
    expect(outputList.children[1].children[0].textContent).toContain('Status')
  })

  it('keeps websocket returnValue separate when the backend explicitly provides it', () => {
    const creator = makeCreator()

    const extracted = creator._extractMethodResponse({
      message: {
        returnValue: 0,
        output: [{ Text: 'Done', Locale: 'en' }]
      }
    }, {
      outputArguments: [
        { Name: 'Status message', DataType: { Identifier: 21 } }
      ]
    })

    expect(extracted.returnValue).toBe(0)
    expect(extracted.outputArguments).toEqual([{ Text: 'Done', Locale: 'en' }])
  })

  it('uses normalized backend method result contract without array-shape inference', () => {
    const creator = makeCreator()

    const extracted = creator._extractMethodResponse({
      callStatus: 'Succeeded',
      returnValue: null,
      outputArguments: [
        ['Id1', 'Id2']
      ],
      rawOutput: [
        ['Id1', 'Id2']
      ]
    }, {
      outputArguments: [
        { Name: 'Identifiers', DataType: { Identifier: 12 }, ValueRank: 1 }
      ]
    })

    expect(extracted.returnValue).toBeUndefined()
    expect(extracted.outputArguments).toEqual([['Id1', 'Id2']])
  })

  it('renders explicit return metadata when provided by the method schema', () => {
    const creator = makeCreator()

    const result = creator.formatMethodResult('MyMethod', {
      callStatus: 'Succeeded',
      returnValue: 0,
      outputArguments: ['Done'],
      rawOutput: [0, 'Done']
    }, {
      returnArgument: { Name: 'StatusCode', DataType: { Identifier: 6 } },
      outputArguments: [{ Name: 'Message', DataType: { Identifier: 12 } }]
    })

    const outputList = result.children[2]
    expect(outputList.children[0].children[0].textContent).toBe('StatusCode')
    expect(outputList.children[1].children[0].textContent).toBe('Message')
  })

  it('surfaces return value and output arguments from direct array payloads', () => {
    const creator = makeCreator()

    const extracted = creator._extractMethodResponse([
      0,
      { pythonclass: 'LocalizedText', Locale: 'en', Text: null }
    ], {
      outputArguments: [
        { Name: 'Status', DataType: { Identifier: 8 } },
        { Name: 'StatusMessage', DataType: { Identifier: 21 } }
      ]
    })
    expect(extracted.returnValue).toBeUndefined()
    expect(extracted.outputArguments).toEqual([
      0,
      { pythonclass: 'LocalizedText', Locale: 'en', Text: null }
    ])

    const result = creator.formatMethodResult('EnableAsset', [
      0,
      { pythonclass: 'LocalizedText', Locale: 'en', Text: null }
    ], {
      outputArguments: [
        { Name: 'Status', DataType: { Identifier: 6 } },
        { Name: 'StatusMessage', DataType: { Identifier: 21 } }
      ]
    })

    expect(result.tagName).toBe('section')
    expect(result.children[0].textContent).toBe('EnableAsset')
  })

  it('treats direct arrays as pure output arguments when output schema exists', () => {
    const creator = makeCreator()

    const extracted = creator._extractMethodResponse(['Joint_1', 'Joint_2'], {
      outputArguments: [
        { Name: 'JointList', DataType: { Identifier: 3028 } },
        { Name: 'Status', DataType: { Identifier: 8 } }
      ]
    })

    expect(extracted.returnValue).toBeUndefined()
    expect(extracted.outputArguments).toEqual(['Joint_1', 'Joint_2'])
  })

  it('formats localized text and arrays into readable result values', () => {
    const creator = makeCreator()

    expect(creator._formatValueForDisplay({ Text: 'Abort requested', Locale: 'en' }, 21)).toBe('Abort requested (en)')
    expect(creator._formatValueForDisplay({ pythonclass: 'LocalizedText', Locale: 'en', Text: null }, 21)).toBe('— (en)')
    expect(creator._formatValueForDisplay([1, 2, 3], 7)).toContain('3 item(s)')
  })

  it('does not expand LocalizedText outputs into Encoding/Locale/Text rows', () => {
    const creator = makeCreator()
    const summary = makeElement('dl')

    const rendered = creator._renderStructuredResultSections(summary, {
      pythonclass: 'LocalizedText',
      Encoding: 0,
      Locale: 'en',
      Text: null
    }, 'Status')

    expect(rendered).toBe(false)
    expect(summary.children).toHaveLength(0)
  })

  it('uses exact field names for generic structure editors', () => {
    const creator = makeCreator()

    expect(creator._structureFieldDefinitions({
      DataType: { Identifier: 9999 },
      FieldDefinitions: [
        { name: 'ExactServerFieldA', dataType: 12 },
        { name: 'ExactServerFieldB', dataType: 7 }
      ]
    })).toEqual([
      { name: 'ExactServerFieldA', label: 'ExactServerFieldA', type: '12' },
      { name: 'ExactServerFieldB', label: 'ExactServerFieldB', type: '7' }
    ])
  })

  it('marks failed method calls explicitly and avoids misleading no-output text', () => {
    const creator = makeCreator()

    const extracted = creator._extractMethodFailure({ error: 'BadInvalidArgument' })
    expect(extracted).toBe('BadInvalidArgument')

    const result = creator.formatMethodResult('GetIdentifiers', { error: 'BadInvalidArgument' }, {
      outputArguments: [{ Name: 'Identifiers', DataType: { Identifier: 12 } }]
    })

    expect(result.tagName).toBe('section')
  })

  it('renders returned output arguments when the OPC UA method status is uncertain', () => {
    const creator = makeCreator()
    const outputs = [
      5,
      { pythonclass: 'LocalizedText', Locale: 'en', Text: 'Failed to parse selection name: "Test"' }
    ]
    const payload = {
      callStatus: 'Uncertain',
      statusCode: { name: 'Uncertain', value: 1073741824, isUncertain: true },
      returnValue: null,
      outputArguments: outputs,
      rawOutput: {
        pythonclass: 'CallMethodResult',
        StatusCode: { value: 1073741824 },
        OutputArguments: outputs
      },
      statusDescription: 'OPC UA method status: The operation was uncertain.(Uncertain)'
    }

    const methodData = {
      outputArguments: [
        { Name: 'Status', DataType: { Identifier: 8 } },
        { Name: 'StatusMessage', DataType: { Identifier: 21 } }
      ]
    }
    const extracted = creator._extractMethodResponse(payload, methodData)

    expect(extracted.callStatus).toBe('Uncertain')
    expect(extracted.outputArguments).toEqual(outputs)
    expect(extracted.rawPayload.pythonclass).toBe('CallMethodResult')

    const result = creator.formatMethodResult('SelectJoiningProcess', payload, methodData)
    const outputList = result.children[2]
    expect(outputList.children[0].children[2].children[0].textContent).toContain('Uncertain')
    expect(outputList.children[1].children[0].textContent).toBe('Status')
    expect(outputList.children[2].children[0].textContent).toBe('StatusMessage')
  })

  it('preserves normalized outputs nested in a legacy rejected websocket payload', () => {
    const creator = makeCreator()
    const outputs = [
      4,
      { pythonclass: 'LocalizedText', Locale: 'en', Text: 'Joining process not found.' }
    ]
    const payload = {
      error: 'OPC UA error: The operation was uncertain.(Uncertain)',
      message: {
        callStatus: 'Uncertain',
        returnValue: null,
        outputArguments: outputs,
        rawOutput: { pythonclass: 'CallMethodResult' },
        exception: 'OPC UA error: The operation was uncertain.(Uncertain)'
      }
    }

    const extracted = creator._extractMethodResponse(payload, {
      outputArguments: [
        { Name: 'Status', DataType: { Identifier: 8 } },
        { Name: 'StatusMessage', DataType: { Identifier: 21 } }
      ]
    })

    expect(extracted.callStatus).toBe('Uncertain')
    expect(extracted.outputArguments).toEqual(outputs)
    expect(extracted.rawPayload).toEqual({ pythonclass: 'CallMethodResult' })
  })

  it('detects array-valued string arguments from ValueRank', () => {
    const creator = makeCreator()

    expect(creator._expectsArrayArgument({ ValueRank: 1 })).toBe(true)
    expect(creator._expectsArrayArgument({ ValueRank: -3 })).toBe(true)
    expect(creator._expectsArrayArgument({ ValueRank: -1 })).toBe(false)
  })

  it('treats TrimmedString arrays as generic string-like array editors', () => {
    const creator = makeCreator()

    expect(creator._isStringLikeArgument({ DataType: { Identifier: 31918 } })).toBe(true)
  })

  it('renders JoiningProcessIdentification with clearer lookup labels and help text', () => {
    const { creator, area } = makeInputCreator()

    const grabValue = creator.createMethodInput(
      makeArg('JoiningProcessIdentification', 3029),
      area,
      ''
    )

    const labels = area.children.filter(child => child?.textContent).map(child => child.textContent)
    expect(labels).toContain('JoiningProcessIdentification  ')

    const wrapper = area.children[1]
    expect(wrapper.classList).toBeDefined()
    expect(wrapper.children[0].textContent).toBe('Specific Id')
    expect(wrapper.children[2].textContent).toBe('OriginId')
    const value = grabValue().value
    expect(value).toHaveLength(3)
  })

  it('reports saved-values as the input source when last-used profile supplies the value', () => {
    const creator = makeCreator()
    expect(
      creator._resolveInputSource(makeArg('Description', 12), 'Saved text', undefined, 'last-used')
    ).toBe('saved-values')
  })

  it('renders generic structure values field-by-field for returned extension-like objects', () => {
    const creator = makeCreator()
    const summary = makeElement('dl')

    const rendered = creator._renderStructuredResultSections(summary, {
      pythonclass: 'MyStructure',
      FieldA: 'Hello',
      FieldB: 2
    }, 'Payload')

    expect(rendered).toBe(true)
    expect(summary.children).toHaveLength(2)
  })

  it('keeps output labels exactly as provided by the server metadata', () => {
    const creator = makeCreator()
    const described = creator._describeOutputArgument(
      { Name: 'StatusMessage', DataType: { Identifier: 21 } },
      { pythonclass: 'LocalizedText', Locale: 'en', Text: 'OK' },
      0
    )

    expect(described.name).toBe('StatusMessage')
  })

  it('keeps Status label unchanged from server metadata', () => {
    const creator = makeCreator()
    const described = creator._describeOutputArgument(
      { Name: 'Status', DataType: { Identifier: 8 } },
      0,
      0
    )

    expect(described.name).toBe('Status')
  })
})
