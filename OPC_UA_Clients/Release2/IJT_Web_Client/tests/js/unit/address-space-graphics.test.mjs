import { describe, expect, it } from 'vitest'
import { formatReadNodeId } from '../../../src/javascripts/views/address-space/address-space-graphics.mjs'

describe('AddressSpaceGraphics read result labels', () => {
  it('falls back when a read response has no nodeid', () => {
    expect(formatReadNodeId({ exception: 'Read failed' })).toBe('unknown node')
  })

  it('formats object node ids from alternate response casing', () => {
    expect(formatReadNodeId({ NodeId: { NamespaceIndex: 2, Identifier: 'Tool1' } })).toBe('ns=2;s=Tool1')
  })

  it('shortens long node ids', () => {
    expect(formatReadNodeId({ nodeid: 'ns=2;s=VeryLongNodeIdentifierForDisplay' })).toBe('...ongNodeIdentifierForDisplay')
  })
})
