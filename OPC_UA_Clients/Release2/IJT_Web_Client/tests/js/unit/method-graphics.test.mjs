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
