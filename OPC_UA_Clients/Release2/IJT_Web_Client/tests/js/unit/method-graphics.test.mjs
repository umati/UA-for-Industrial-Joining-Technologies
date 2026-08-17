import { describe, expect, it, vi } from 'vitest'
import MethodGraphics from '../../../src/javascripts/views/methods/method-graphics.mjs'

describe('MethodGraphics activation lifecycle', () => {
  it('shares one discovery operation across concurrent activation signals', async () => {
    let finishActivation
    const activation = new Promise(resolve => {
      finishActivation = resolve
    })
    const graphics = Object.create(MethodGraphics.prototype)
    graphics.activationPromise = null
    graphics._activate = vi.fn(() => activation)

    const first = graphics.activate()
    const second = graphics.activate()

    expect(second).toBe(first)
    expect(graphics._activate).toHaveBeenCalledTimes(1)

    finishActivation()
    await first
    expect(graphics.activationPromise).toBeNull()
  })
})

describe('MethodGraphics discovery parsing', () => {
  it('extracts primary output list from normalized method-call payload', () => {
    const graphics = Object.create(MethodGraphics.prototype)
    const payload = {
      outputArguments: [
        [{ JointId: 'Joint-1' }, { JointId: 'Joint-2' }],
        0
      ]
    }
    expect(graphics._extractPrimaryOutputList(payload)).toEqual([{ JointId: 'Joint-1' }, { JointId: 'Joint-2' }])
  })

  it('resolves detected signals from GetIOSignals outputArguments payload', async () => {
    const graphics = Object.create(MethodGraphics.prototype)
    graphics.methodState = { productInstanceUri: 'urn:tool:1', detectedSignals: [] }
    graphics.methodManager = {
      getMethod: vi.fn(() => ({
        arguments: [{ DataType: { Identifier: '12' } }, { DataType: { Identifier: '31918' } }]
      })),
      call: vi.fn(async () => ({
        outputArguments: [[
          { SignalId: '55' },
          { Value: { SignalId: '77' } }
        ]]
      }))
    }

    await graphics.resolveDetectedSignals()

    expect(graphics.methodState.detectedSignals).toEqual(['55', '77'])
  })
})
