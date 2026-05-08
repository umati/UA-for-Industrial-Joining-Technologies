import { describe, expect, it } from 'vitest'
import JointDemo from '../../../src/javascripts/views/standard-demo/joint-demo.mjs'

function makeDemo ({
  selected = null,
  settingsProductId = '',
  detectedProductInstanceUri = '',
} = {}) {
  const demo = Object.create(JointDemo.prototype)
  demo._selectedProductInstanceUri = selected
  demo.settings = { productId: settingsProductId }
  demo._detectedTools = detectedProductInstanceUri
    ? [{ toolName: 'Tool 1', productInstanceUri: detectedProductInstanceUri, path: '0:TighteningSystem/2:Assets/2:Tools/2:Tool_1' }]
    : []
  return demo
}

describe('JointDemo ProductInstanceUri resolution', () => {
  it('uses the explicitly selected server tool URI first', () => {
    const demo = makeDemo({
      selected: 'www.example.com/selected-tool',
      settingsProductId: 'www.example.com/manual-tool',
      detectedProductInstanceUri: 'www.example.com/detected-tool',
    })

    expect(demo._getProductUri()).toBe('www.example.com/selected-tool')
  })

  it('uses a manual non-sample Settings URI before auto-detected tools', () => {
    const demo = makeDemo({
      settingsProductId: 'www.example.com/manual-tool',
      detectedProductInstanceUri: 'www.example.com/detected-tool',
    })

    expect(demo._getProductUri()).toBe('www.example.com/manual-tool')
  })

  it('prefers the detected server tool over the bundled company sample URI', () => {
    const demo = makeDemo({
      settingsProductId: 'www.company.com/ProductABC123',
      detectedProductInstanceUri: 'www.atlascopco.com/53F22F10-B313-4B1D-924C-3A3EC7FCA002',
    })

    expect(demo._getProductUri()).toBe('www.atlascopco.com/53F22F10-B313-4B1D-924C-3A3EC7FCA002')
  })

  it('prefers the detected server tool over the bundled cable sample URI', () => {
    const demo = makeDemo({
      settingsProductId: 'www.atlascopco.com/CABLE-B0000000-',
      detectedProductInstanceUri: 'www.atlascopco.com/53F22F10-B313-4B1D-924C-3A3EC7FCA002',
    })

    expect(demo._getProductUri()).toBe('www.atlascopco.com/53F22F10-B313-4B1D-924C-3A3EC7FCA002')
  })

  it('keeps a sample Settings URI as a last-resort fallback when no server tool is loaded', () => {
    const demo = makeDemo({
      settingsProductId: 'www.atlascopco.com/CABLE-B0000000-',
    })

    expect(demo._getProductUri()).toBe('www.atlascopco.com/CABLE-B0000000-')
  })

  it('does not allow demo method calls with only a bundled sample URI', () => {
    const demo = makeDemo({
      settingsProductId: 'www.atlascopco.com/CABLE-B0000000-',
    })

    expect(demo._callableProductUri()).toBe('')
  })

  it('allows demo method calls once server discovery resolves the tool URI', () => {
    const demo = makeDemo({
      settingsProductId: 'www.atlascopco.com/CABLE-B0000000-',
      detectedProductInstanceUri: 'www.atlascopco.com/53F22F10-B313-4B1D-924C-3A3EC7FCA002',
    })

    expect(demo._callableProductUri()).toBe('www.atlascopco.com/53F22F10-B313-4B1D-924C-3A3EC7FCA002')
  })
})
