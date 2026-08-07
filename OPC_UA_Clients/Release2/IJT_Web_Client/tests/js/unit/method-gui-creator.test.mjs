import { describe, expect, it } from 'vitest'
import MethodGUICreator from '../../../src/javascripts/views/methods/method-gui-creator.mjs'

function makeCreator () {
  return new MethodGUICreator({}, {}, {}, {})
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

function makeInputCreator () {
  const screen = {
    createLabel: () => ({ classList: makeClassList() }),
    createDropdown: () => {
      const options = []
      return {
        classList: makeClassList(),
        select: { value: '' },
        addOption: (label, value) => options.push({ label, value }),
        get value () { return this.select.value },
        options
      }
    }
  }
  const area = { children: [], appendChild (child) { this.children.push(child) } }
  return { creator: new MethodGUICreator(screen, {}, {}, {}), area }
}

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
      { methodProductInstanceUri: 'urn:server:tool:1' }
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

    const dropdown = area.children[1]
    expect(dropdown.options).toEqual([
      { label: 'BATCH (3)', value: 3 },
      { label: 'SYNC (2)', value: 2 }
    ])
    expect(dropdown.select.value).toBe('3')
    expect(grabValue().value).toBe(3)
  })

  it('resolves ProductInstanceUri defaults from settings metadata source', () => {
    const creator = new MethodGUICreator({}, {}, {}, { productId: 'urn:test:tool:1' })

    const value = creator.resolveMetadataDefault({ source: 'productid', allowEmpty: false })

    expect(value).toBe('urn:test:tool:1')
  })

  it('prefers the server-discovered Tool.ProductInstanceUri over Settings fallback', () => {
    const creator = new MethodGUICreator({}, {}, {}, {
      methodProductInstanceUri: 'urn:server:tool:2',
      productId: 'urn:settings:tool:1'
    })

    const value = creator.resolveMetadataDefault({ source: 'productid', allowEmpty: false })

    expect(value).toBe('urn:server:tool:2')
  })

  it('resolves current UTC defaults for SetTime', () => {
    const creator = makeCreator()

    const value = creator.resolveMetadataDefault({ source: 'currentUtc' })

    expect(Number.isNaN(Date.parse(value))).toBe(false)
    expect(value).toMatch(/Z$/)
  })

  it('formats method results with method name and indented payload', () => {
    const creator = makeCreator()

    const result = creator.formatMethodResult('GetJointList', { output: [1, 2, 3] })

    expect(result).toContain('"method": "GetJointList"')
    expect(result).toContain('"output"')
  })
})
