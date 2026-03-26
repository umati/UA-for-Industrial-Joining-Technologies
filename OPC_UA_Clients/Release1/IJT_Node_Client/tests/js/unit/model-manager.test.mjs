import { describe, it, expect, beforeEach } from 'vitest'
import { ModelManager } from '../../../javascripts/ijt-support/models/model-manager.mjs'
import { LocalizationModel } from '../../../javascripts/ijt-support/models/support-models.mjs'

describe('ModelManager', () => {
  let mm

  beforeEach(() => {
    mm = new ModelManager()
  })

  describe('factory()', () => {
    it('returns primitive values as-is', () => {
      expect(mm.factory('name', 'hello', null)).toBe('hello')
      expect(mm.factory('count', 42, null)).toBe(42)
    })

    it('returns array as-is (arrays are handled by caller)', () => {
      const arr = [1, 2, 3]
      expect(mm.factory('items', arr, null)).toBe(arr)
    })

    it('returns LocalizationModel for content with locale field', () => {
      const result = mm.factory('name', { locale: 'en', text: 'Test' }, null)
      expect(result).toBeInstanceOf(LocalizationModel)
    })

    it('returns LocalizationModel for content with key field', () => {
      const result = mm.factory('pair', { key: 'myKey', value: 'myVal' }, null)
      expect(result).toBeInstanceOf(LocalizationModel)
    })

    it('extracts value from ExtensionObject wrapper', () => {
      const inner = { locale: 'en', text: 'Extracted' }
      const result = mm.factory('name', { dataType: 'ExtensionObject', value: inner }, null)
      expect(result).toBeInstanceOf(LocalizationModel)
    })

    it('uses castMapping to pick correct model class', async () => {
      const { default: ProcessingTimesDataType } = await import('../../../javascripts/ijt-support/models/processing-times-data-type.mjs')
      const result = mm.factory('processingTimes', { startTime: '2024-01-01' }, { processingTimes: 'ProcessingTimesDataType' })
      expect(result).toBeInstanceOf(ProcessingTimesDataType)
    })
  })

  describe('createModelFromRead()', () => {
    it('returns null if values has no resultId', () => {
      const result = mm.createModelFromRead({ someOtherField: 'value' })
      expect(result).toBeNull()
    })
  })

  describe('createModelFromEvent()', () => {
    it('returns DefaultNode for TighteningSystemType event', async () => {
      const { DefaultNode } = await import('../../../javascripts/ijt-support/models/default-node.mjs')
      const msg = {
        EventType: { value: 'TighteningSystemType' },
        browseData: {},
        relations: []
      }
      const result = mm.createModelFromEvent(msg)
      expect(result).toBeInstanceOf(DefaultNode)
    })

    it('returns DefaultNode for unknown event type', async () => {
      const { DefaultNode } = await import('../../../javascripts/ijt-support/models/default-node.mjs')
      const msg = {
        EventType: { value: 'UnknownType' },
        browseData: {},
        relations: []
      }
      const result = mm.createModelFromEvent(msg)
      expect(result).toBeInstanceOf(DefaultNode)
    })
  })
})
