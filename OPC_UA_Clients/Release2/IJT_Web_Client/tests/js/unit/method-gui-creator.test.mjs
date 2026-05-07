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
})
