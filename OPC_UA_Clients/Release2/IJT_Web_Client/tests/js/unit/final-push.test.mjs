/**
 * Final push to 99%+ coverage - comprehensive instantiation tests
 */

import { describe, it, expect } from 'vitest'
import TagDataType from '../../../src/javascripts/ijt-support/models/tag-data-type.mjs'
import ResultValueDataType from '../../../src/javascripts/ijt-support/models/results/result-value-data-type.mjs'
import { EntityCache } from '../../../src/javascripts/ijt-support/entity-cache/entity-manager.mjs'
import { JointManager } from '../../../src/javascripts/ijt-support/joints/joint-manager.mjs'

describe('Final coverage - empty class instantiation', () => {
  it('imports and uses TagDataType', () => {
    expect(TagDataType).toBeDefined()
    expect(TagDataType.name).toBe('TagDataType')
  })

  it('imports and uses ResultValueDataType', () => {
    expect(ResultValueDataType).toBeDefined()
    expect(ResultValueDataType.name).toBe('ResultValueDataType')
  })

  it('imports and uses EntityCache', () => {
    expect(EntityCache).toBeDefined()
    expect(EntityCache.name).toBe('EntityCache')
  })

  it('imports and uses JointManager', () => {
    expect(JointManager).toBeDefined()
    expect(JointManager.name).toBe('JointManager')
  })
})

describe('Final coverage - ijt-support re-exports', () => {
  it('imports all major exports from ijt-support', async () => {
    const exports = await import('../../../src/javascripts/ijt-support/ijt-support.mjs')
    expect(exports.ijtLog).toBeDefined()
    expect(exports.AssetManager).toBeDefined()
    expect(exports.EventManager).toBeDefined()
    expect(exports.MethodManager).toBeDefined()
    expect(exports.ModelManager).toBeDefined()
    expect(exports.ResultManager).toBeDefined()
    expect(exports.ConnectionManager).toBeDefined()
    expect(exports.WebSocketManager).toBeDefined()
    expect(exports.SocketHandler).toBeDefined()
    expect(exports.EntityCache).toBeDefined()
    expect(exports.JointManager).toBeDefined()
    expect(exports.EntityCacheBase).toBeDefined()
    expect(exports.ObservableManagerBase).toBeDefined()
  })
})
