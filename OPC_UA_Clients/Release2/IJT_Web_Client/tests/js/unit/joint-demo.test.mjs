import { describe, expect, it } from 'vitest'
import JointDemo from '../../../src/javascripts/views/standard-demo/joint-demo.mjs'

function makeDemo ({
  selected = null,
  settingsProductId = '',
  detectedProductInstanceUri = '',
  detectedJoints = [],
} = {}) {
  const demo = Object.create(JointDemo.prototype)
  demo._selectedProductInstanceUri = selected
  demo.settings = { productId: settingsProductId, Joint1: 'Configured_1', Joint2: 'Configured_2' }
  demo._detectedTools = detectedProductInstanceUri
    ? [{ toolName: 'Tool 1', productInstanceUri: detectedProductInstanceUri, path: '0:TighteningSystem/2:Assets/2:Tools/2:Tool_1' }]
    : []
  demo._detectedJoints = detectedJoints
  demo._jointButtons = []
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

  it('uses server-discovered joint IDs before Settings defaults', () => {
    const demo = makeDemo({ detectedJoints: ['ServerJointA', 'ServerJointB'] })

    expect(demo._jointIdForButton(0)).toBe('ServerJointA')
    expect(demo._jointIdForButton(1)).toBe('ServerJointB')
  })

  it('falls back to the first discovered joint when the server exposes one joint', () => {
    const demo = makeDemo({ detectedJoints: ['OnlyServerJoint'] })

    expect(demo._jointIdForButton(0)).toBe('OnlyServerJoint')
    expect(demo._jointIdForButton(1)).toBe('OnlyServerJoint')
  })

  it('parses JointIds from GetJointList method output shapes', () => {
    const demo = makeDemo()
    const output = [[
      { JointId: 'Joint-A' },
      { Value: { JointMetaData: { JointId: 'Joint-B' } } },
      'Joint-C',
      { JointId: 'Joint-A' },
    ]]

    expect(demo._extractJointIds(output)).toEqual(['Joint-A', 'Joint-B', 'Joint-C'])
  })
})
