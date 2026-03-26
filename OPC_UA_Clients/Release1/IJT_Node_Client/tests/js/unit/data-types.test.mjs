import { describe, it, expect } from 'vitest'
import ErrorInformationDataType from '../../../javascripts/ijt-support/models/error-information-data-type.mjs'
import ProcessingTimesDataType from '../../../javascripts/ijt-support/models/processing-times-data-type.mjs'
import ResultValueDataType from '../../../javascripts/ijt-support/models/result-value-data-type.mjs'
import StepResultDataType from '../../../javascripts/ijt-support/models/step-result-data-type.mjs'
import TighteningResultDataType from '../../../javascripts/ijt-support/models/tightening-result-data-type.mjs'
import { TighteningTraceDataType, StepTraceDataType, TraceContentDataType, TraceValueDataType } from '../../../javascripts/ijt-support/models/tightening-trace-data-type.mjs'
import TagDataType from '../../../javascripts/ijt-support/models/tag-data-type.mjs'
import IJTBaseModel from '../../../javascripts/ijt-support/models/ijt-base-model.mjs'

// Minimal model manager that returns primitive values unchanged
const stubMM = { factory: (_key, val) => val }

describe('Data Type Models', () => {
  describe('ErrorInformationDataType', () => {
    it('constructs without throwing', () => {
      expect(() => new ErrorInformationDataType({}, stubMM)).not.toThrow()
    })

    it('extends IJTBaseModel', () => {
      expect(new ErrorInformationDataType({}, stubMM)).toBeInstanceOf(IJTBaseModel)
    })

    it('stores errorId property', () => {
      const dt = new ErrorInformationDataType({ errorId: 42 }, stubMM)
      expect(dt.errorId).toBe(42)
    })
  })

  describe('ProcessingTimesDataType', () => {
    it('constructs without throwing', () => {
      expect(() => new ProcessingTimesDataType({}, stubMM)).not.toThrow()
    })

    it('extends IJTBaseModel', () => {
      expect(new ProcessingTimesDataType({}, stubMM)).toBeInstanceOf(IJTBaseModel)
    })

    it('stores startTime property', () => {
      const dt = new ProcessingTimesDataType({ startTime: '2024-01-01T00:00:00Z' }, stubMM)
      expect(dt.startTime).toBe('2024-01-01T00:00:00Z')
    })
  })

  describe('ResultValueDataType', () => {
    it('constructs without throwing', () => {
      expect(() => new ResultValueDataType({}, stubMM)).not.toThrow()
    })

    it('extends IJTBaseModel', () => {
      expect(new ResultValueDataType({}, stubMM)).toBeInstanceOf(IJTBaseModel)
    })

    it('stores name and value', () => {
      const dt = new ResultValueDataType({ name: 'Torque', measurementValue: 15.5 }, stubMM)
      expect(dt.name).toBe('Torque')
      expect(dt.measurementValue).toBe(15.5)
    })
  })

  describe('StepResultDataType', () => {
    it('constructs without throwing', () => {
      expect(() => new StepResultDataType({}, stubMM)).not.toThrow()
    })

    it('extends IJTBaseModel', () => {
      expect(new StepResultDataType({}, stubMM)).toBeInstanceOf(IJTBaseModel)
    })

    it('getIdentifier() returns stepResultId', () => {
      const dt = new StepResultDataType({ stepResultId: 'step-1' }, stubMM)
      expect(dt.getIdentifier()).toBe('step-1')
    })
  })

  describe('TighteningResultDataType', () => {
    it('constructs with empty data without throwing', () => {
      expect(() => new TighteningResultDataType({}, stubMM)).not.toThrow()
    })

    it('extends IJTBaseModel', () => {
      expect(new TighteningResultDataType({}, stubMM)).toBeInstanceOf(IJTBaseModel)
    })

    it('stores overallStatus', () => {
      const dt = new TighteningResultDataType({ overallStatus: 1 }, stubMM)
      expect(dt.overallStatus).toBe(1)
    })
  })

  describe('TighteningTraceDataType', () => {
    it('constructs without throwing', () => {
      expect(() => new TighteningTraceDataType({}, stubMM)).not.toThrow()
    })

    it('extends IJTBaseModel', () => {
      expect(new TighteningTraceDataType({}, stubMM)).toBeInstanceOf(IJTBaseModel)
    })

    it('getIdentifier() returns traceId', () => {
      const dt = new TighteningTraceDataType({ traceId: 'trace-abc' }, stubMM)
      expect(dt.getIdentifier()).toBe('trace-abc')
    })
  })

  describe('StepTraceDataType', () => {
    it('constructs without throwing', () => {
      expect(() => new StepTraceDataType({}, stubMM)).not.toThrow()
    })

    it('getIdentifier() returns stepTraceId', () => {
      const dt = new StepTraceDataType({ stepTraceId: 'st-1' }, stubMM)
      expect(dt.getIdentifier()).toBe('st-1')
    })
  })

  describe('TraceContentDataType', () => {
    it('constructs without throwing', () => {
      expect(() => new TraceContentDataType({}, stubMM)).not.toThrow()
    })
  })

  describe('TraceValueDataType', () => {
    it('constructs without throwing', () => {
      expect(() => new TraceValueDataType({}, stubMM)).not.toThrow()
    })
  })

  describe('TagDataType', () => {
    it('constructs without throwing', () => {
      expect(() => new TagDataType({}, stubMM)).not.toThrow()
    })

    it('extends IJTBaseModel', () => {
      expect(new TagDataType({}, stubMM)).toBeInstanceOf(IJTBaseModel)
    })

    it('stores location property', () => {
      const dt = new TagDataType({ location: 'Bolt1' }, stubMM)
      expect(dt.location).toBe('Bolt1')
    })
  })
})
