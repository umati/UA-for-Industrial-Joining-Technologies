/**
 * Tests for the IJT OPC UA data-model classes.
 *
 * Coverage targets:
 *   - IJTBaseModel           (ijt-base-model.mjs)   — primitive, array, object fields
 *   - ResultDataModel        (result-data-model.mjs) — constructs via castMapping
 *   - TighteningResultDataType (tightening-result-data-type.mjs) — getStep()
 *   - StepResultDataType     (step-result-data-type.mjs)         — getIdentifier()
 *   - TighteningTraceDataType (tightening-trace-data-type.mjs)   — getStepTrace(), createConnections()
 *   - StepTraceDataType      (same file)             — getIdentifier()
 *   - ErrorInformationDataType (error-information-data-type.mjs) — simple construction
 *   - ModelManager.createModelFromNode()             — switch branches
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { ModelManager } from '../../../javascripts/ijt-support/models/model-manager.mjs'
import IJTBaseModel from '../../../javascripts/ijt-support/models/ijt-base-model.mjs'
import ResultDataModel from '../../../javascripts/ijt-support/models/result-data-model.mjs'
import TighteningResultDataType from '../../../javascripts/ijt-support/models/tightening-result-data-type.mjs'
import StepResultDataType from '../../../javascripts/ijt-support/models/step-result-data-type.mjs'
import { TighteningTraceDataType, StepTraceDataType } from '../../../javascripts/ijt-support/models/tightening-trace-data-type.mjs'
import ErrorInformationDataType from '../../../javascripts/ijt-support/models/error-information-data-type.mjs'
import ProcessingTimesDataType from '../../../javascripts/ijt-support/models/processing-times-data-type.mjs'
import { DefaultNode } from '../../../javascripts/ijt-support/models/default-node.mjs'
import { LocalizationModel } from '../../../javascripts/ijt-support/models/support-models.mjs'

// ── Minimal ModelManager for tests that call super(params, mm) ──────────────
function makeModelManager () {
  return new ModelManager()
}

// ─────────────────────────────────────────────────────────────────────────────
describe('IJTBaseModel', () => {
  let mm

  beforeEach(() => { mm = makeModelManager() })

  it('stores primitive string values directly', () => {
    const model = new IJTBaseModel({ name: 'TestResult', status: 'OK' }, mm, null)
    expect(model.name).toBe('TestResult')
    expect(model.status).toBe('OK')
  })

  it('stores primitive number values directly', () => {
    const model = new IJTBaseModel({ torque: 42.5, angle: 180 }, mm, null)
    expect(model.torque).toBe(42.5)
    expect(model.angle).toBe(180)
  })

  it('stores primitive boolean values directly', () => {
    const model = new IJTBaseModel({ overallResult: true }, mm, null)
    expect(model.overallResult).toBe(true)
  })

  it('stores original parameters in debugValues', () => {
    const params = { resultId: 'abc-123', torque: 15.0 }
    const model = new IJTBaseModel(params, mm, null)
    expect(model.debugValues).toBe(params)
  })

  it('processes array fields by calling factory on each element', () => {
    const params = { tags: [42, 99] }
    const model = new IJTBaseModel(params, mm, null)
    expect(model.tags).toEqual([42, 99])
  })

  it('processes object fields through factory', () => {
    const params = { meta: { key: 'toolId', value: 'T-001' } }
    const model = new IJTBaseModel(params, mm, null)
    expect(model.meta).toBeDefined()
  })

  it('applies castMapping for known type names in arrays', () => {
    const params = { stepResults: [{ stepResultId: 'step-1', stepResultValues: [] }] }
    const castMapping = { stepresults: 'StepResultDataType' }
    const model = new IJTBaseModel(params, mm, castMapping)
    expect(model.stepResults).toHaveLength(1)
    expect(model.stepResults[0]).toBeInstanceOf(StepResultDataType)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
describe('ErrorInformationDataType', () => {
  let mm

  beforeEach(() => { mm = makeModelManager() })

  it('constructs from simple parameters', () => {
    const error = new ErrorInformationDataType({ errorId: 42, message: 'Torque limit exceeded' }, mm)
    expect(error.errorId).toBe(42)
    expect(error.message).toBe('Torque limit exceeded')
  })

  it('is an instance of IJTBaseModel', () => {
    const error = new ErrorInformationDataType({ errorId: 1 }, mm)
    expect(error).toBeInstanceOf(IJTBaseModel)
  })

  it('stores debugValues', () => {
    const params = { errorId: 7 }
    const error = new ErrorInformationDataType(params, mm)
    expect(error.debugValues).toBe(params)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
describe('StepResultDataType', () => {
  let mm

  beforeEach(() => { mm = makeModelManager() })

  it('constructs and stores stepResultId', () => {
    const step = new StepResultDataType({ stepResultId: 'step-A' }, mm)
    expect(step.stepResultId).toBe('step-A')
  })

  it('getIdentifier() returns stepResultId', () => {
    const step = new StepResultDataType({ stepResultId: 'step-42' }, mm)
    expect(step.getIdentifier()).toBe('step-42')
  })

  it('processes stepResultValues array when provided', () => {
    const step = new StepResultDataType(
      { stepResultId: 'step-1', stepResultValues: [{ name: 'Torque', measurementValue: 15 }] },
      mm
    )
    expect(step.stepResultValues).toHaveLength(1)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
describe('StepTraceDataType', () => {
  let mm

  beforeEach(() => { mm = makeModelManager() })

  it('constructs and stores stepTraceId', () => {
    const step = new StepTraceDataType({ stepTraceId: 'trace-step-1' }, mm)
    expect(step.stepTraceId).toBe('trace-step-1')
  })

  it('getIdentifier() returns stepTraceId', () => {
    const step = new StepTraceDataType({ stepTraceId: 'trace-step-99' }, mm)
    expect(step.getIdentifier()).toBe('trace-step-99')
  })
})

// ─────────────────────────────────────────────────────────────────────────────
describe('TighteningTraceDataType', () => {
  let mm

  beforeEach(() => { mm = makeModelManager() })

  it('constructs and stores traceId', () => {
    const trace = new TighteningTraceDataType({ traceId: 'trace-001' }, mm)
    expect(trace.traceId).toBe('trace-001')
  })

  it('getIdentifier() returns traceId', () => {
    const trace = new TighteningTraceDataType({ traceId: 'trace-007' }, mm)
    expect(trace.getIdentifier()).toBe('trace-007')
  })

  it('getStepTrace() returns the matching step by stepTraceId', () => {
    const trace = new TighteningTraceDataType(
      {
        traceId: 'T1',
        stepTraces: [{ stepTraceId: 'step-A' }, { stepTraceId: 'step-B' }]
      },
      mm
    )
    const found = trace.getStepTrace('step-A')
    expect(found).toBeDefined()
    expect(found.getIdentifier()).toBe('step-A')
  })

  it('getStepTrace() returns the second step when first does not match', () => {
    const trace = new TighteningTraceDataType(
      {
        traceId: 'T1',
        stepTraces: [{ stepTraceId: 'step-A' }, { stepTraceId: 'step-B' }]
      },
      mm
    )
    const found = trace.getStepTrace('step-B')
    expect(found.getIdentifier()).toBe('step-B')
  })

  it('getStepTrace() throws when stepTraceId not found', () => {
    const trace = new TighteningTraceDataType(
      { traceId: 'T1', stepTraces: [{ stepTraceId: 'step-A' }] },
      mm
    )
    expect(() => trace.getStepTrace('does-not-exist')).toThrow()
  })

  it('createConnections() links trace step to result step', () => {
    const traceStep = new StepTraceDataType({ stepTraceId: 'ts-1', stepResultId: 'sr-1' }, mm)
    const trace = new TighteningTraceDataType({ traceId: 'T1', stepTraces: [] }, mm)
    trace.stepTraces = [traceStep]

    const resultStep = new StepResultDataType({ stepResultId: 'sr-1' }, mm)
    const resultContent = { getStep: (id) => id === 'sr-1' ? resultStep : undefined }

    trace.createConnections(resultContent)

    // Check traceStep link using property access (avoids circular toEqual issues)
    expect(traceStep.stepResultId.type).toBe('linkedValue')
    expect(traceStep.stepResultId.value).toBe('sr-1')
    expect(traceStep.stepResultId.link).toBe(resultStep)

    // Check resultStep back-link
    expect(resultStep.stepTraceId.type).toBe('linkedValue')
    expect(resultStep.stepTraceId.link).toBe(traceStep)
  })

  it('createConnections() returns early when matching result step not found', () => {
    const traceStep = new StepTraceDataType({ stepTraceId: 'ts-1', stepResultId: 'sr-999' }, mm)
    const trace = new TighteningTraceDataType({ traceId: 'T1', stepTraces: [] }, mm)
    trace.stepTraces = [traceStep]
    const resultContent = { getStep: () => undefined }
    // Should not throw and traceStep.stepResultId stays as original string
    expect(() => trace.createConnections(resultContent)).not.toThrow()
    expect(traceStep.stepResultId).toBe('sr-999')
  })

  it('createConnections() throws when stepTraces property is missing', () => {
    const trace = new TighteningTraceDataType({ traceId: 'T1' }, mm)
    delete trace.stepTraces
    expect(() => trace.createConnections({})).toThrow('No steps in the trace')
  })
})

// ─────────────────────────────────────────────────────────────────────────────
describe('TighteningResultDataType', () => {
  let mm

  beforeEach(() => { mm = makeModelManager() })

  it('constructs and stores resultId', () => {
    const result = new TighteningResultDataType({ resultId: 'R-001' }, mm)
    expect(result.resultId).toBe('R-001')
  })

  it('getStep() returns the matching step by stepResultId', () => {
    const result = new TighteningResultDataType(
      {
        resultId: 'R-001',
        stepResults: [{ stepResultId: 'step-1' }, { stepResultId: 'step-2' }]
      },
      mm
    )
    const found = result.getStep('step-1')
    expect(found).toBeDefined()
    expect(found.getIdentifier()).toBe('step-1')
  })

  it('getStep() returns the second step when first does not match', () => {
    const result = new TighteningResultDataType(
      {
        resultId: 'R-001',
        stepResults: [{ stepResultId: 'step-1' }, { stepResultId: 'step-2' }]
      },
      mm
    )
    const found = result.getStep('step-2')
    expect(found.getIdentifier()).toBe('step-2')
  })

  it('getStep() returns undefined when step not found in non-empty list', () => {
    const result = new TighteningResultDataType(
      { resultId: 'R-001', stepResults: [{ stepResultId: 'step-1' }] },
      mm
    )
    const found = result.getStep('does-not-exist')
    expect(found).toBeUndefined()
  })

  it('getStep() throws when stepResults is empty array', () => {
    const result = new TighteningResultDataType({ resultId: 'R-001', stepResults: [] }, mm)
    expect(() => result.getStep('step-1')).toThrow()
  })

  it('getStep() throws when stepResults field is not present', () => {
    const result = new TighteningResultDataType({ resultId: 'R-001' }, mm)
    expect(() => result.getStep('step-1')).toThrow()
  })
})

// ─────────────────────────────────────────────────────────────────────────────
describe('ResultDataModel', () => {
  let mm

  beforeEach(() => { mm = makeModelManager() })

  it('constructs with resultId and basic fields', () => {
    const model = new ResultDataModel({ resultId: 'RES-42', overallResult: 0 }, mm)
    expect(model.resultId).toBe('RES-42')
    expect(model.overallResult).toBe(0)
  })

  it('is an instance of IJTBaseModel', () => {
    const model = new ResultDataModel({ resultId: 'R-001' }, mm)
    expect(model).toBeInstanceOf(IJTBaseModel)
  })

  it('applies processingTimes castMapping to create ProcessingTimesDataType', () => {
    const model = new ResultDataModel(
      { resultId: 'R-002', processingTimes: { startTime: '2024-01-01', endTime: '2024-01-01' } },
      mm
    )
    expect(model.processingTimes).toBeInstanceOf(ProcessingTimesDataType)
  })

  it('processes tags array as TagDataType instances', async () => {
    const { default: TagDataType } = await import('../../../javascripts/ijt-support/models/tag-data-type.mjs')
    const model = new ResultDataModel(
      { resultId: 'R-003', tags: [{ location: 'A' }] },
      mm
    )
    expect(model.tags).toHaveLength(1)
    expect(model.tags[0]).toBeInstanceOf(TagDataType)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
describe('ModelManager.createModelFromNode()', () => {
  let mm

  beforeEach(() => { mm = makeModelManager() })

  it('returns DefaultNode for TighteningSystemType', () => {
    const node = { typeDefinition: 'TighteningSystemType', browseData: {}, relations: [] }
    const result = mm.createModelFromNode(node)
    expect(result).toBeInstanceOf(DefaultNode)
  })

  it('returns DefaultNode for ResultManagementType', () => {
    const node = { typeDefinition: 'ResultManagementType', browseData: {}, relations: [] }
    const result = mm.createModelFromNode(node)
    expect(result).toBeInstanceOf(DefaultNode)
  })

  it('sets node.model property after creating model', () => {
    const node = { typeDefinition: 'TighteningSystemType', browseData: {}, relations: [] }
    const result = mm.createModelFromNode(node)
    expect(node.model).toBe(result)
  })

  it('returns DefaultNode for unknown typeDefinition', () => {
    const node = { typeDefinition: 'UnknownType', browseData: {}, relations: [] }
    const result = mm.createModelFromNode(node)
    expect(result).toBeInstanceOf(DefaultNode)
  })

  it('returns ResultDataModel for ns=4;i=2001 typeDefinition', () => {
    const node = {
      typeDefinition: 'ns=4;i=2001',
      model: null,
      value: { value: { resultId: 'R-001', overallResult: 0 } }
    }
    const result = mm.createModelFromNode(node)
    expect(result).toBeInstanceOf(ResultDataModel)
  })

  it('returns ResultDataModel for ns=1;i=2001 typeDefinition', () => {
    const node = {
      typeDefinition: 'ns=1;i=2001',
      model: null,
      value: { value: { resultId: 'R-002', overallResult: 1 } }
    }
    const result = mm.createModelFromNode(node)
    expect(result).toBeInstanceOf(ResultDataModel)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
describe('ModelManager.createModelFromEvent() — additional branches', () => {
  let mm

  beforeEach(() => { mm = makeModelManager() })

  it('handles ResultManagementType event type', () => {
    const msg = {
      EventType: { value: 'ResultManagementType' },
      browseData: {},
      relations: []
    }
    const result = mm.createModelFromEvent(msg)
    expect(result).toBeInstanceOf(DefaultNode)
  })

  it('handles ns=X;i=1007 event with Result.value → ResultDataModel', () => {
    const msg = {
      EventType: { value: 'ns=7;i=1007' },
      Result: { value: { resultId: 'R-event-001', overallResult: 0 } }
    }
    const result = mm.createModelFromEvent(msg)
    expect(result).toBeInstanceOf(ResultDataModel)
  })

  it('falls back to DefaultNode for ns=X;i=1007 without Result.value', () => {
    const msg = {
      EventType: { value: 'ns=7;i=1007' },
      browseData: {},
      relations: []
      // No Result field — msg?.Result?.value is undefined → falsy → DefaultNode
    }
    const result = mm.createModelFromEvent(msg)
    expect(result).toBeInstanceOf(DefaultNode)
  })

  it('eventTypeIdOf handles EventType.value as object with toString', () => {
    const msg = {
      EventType: { value: { toString: () => 'TighteningSystemType' } },
      browseData: {},
      relations: []
    }
    const result = mm.createModelFromEvent(msg)
    expect(result).toBeInstanceOf(DefaultNode)
  })

  it('eventTypeIdOf returns empty string for missing EventType', () => {
    const msg = { browseData: {}, relations: [] }
    const result = mm.createModelFromEvent(msg)
    expect(result).toBeInstanceOf(DefaultNode)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
describe('ModelManager.factory() — additional branches', () => {
  let mm

  beforeEach(() => { mm = makeModelManager() })

  it('returns plain object when no castMapping and no locale/key fields', () => {
    const obj = { someField: 'data', anotherField: 123 }
    const result = mm.factory('customField', obj, null)
    expect(result).toBe(obj)
  })

  it('castMapping match is case-insensitive for parameter name', () => {
    const result = mm.factory(
      'ProcessingTimes',
      { startTime: '2024-01-01' },
      { processingTimes: 'ProcessingTimesDataType' }
    )
    expect(result).toBeInstanceOf(ProcessingTimesDataType)
  })

  it('returns content as-is when castMapping name not in modelRegistry', () => {
    const content = { data: 'value' }
    const result = mm.factory('myField', content, { myField: 'NonExistentType' })
    expect(result).toBe(content)
  })

  it('extracts value from ExtensionObject and routes to locale handling', () => {
    const result = mm.factory('name', {
      dataType: 'ExtensionObject',
      value: { locale: 'de', text: 'Werkzeug' }
    }, null)
    expect(result).toBeInstanceOf(LocalizationModel)
  })

  it('key with empty value stores empty string in LocalizationModel', () => {
    const result = mm.factory('pair', { key: 'toolId', value: '' }, null)
    expect(result).toBeInstanceOf(LocalizationModel)
  })

  it('returns content unchanged for empty object with no special fields', () => {
    const obj = {}
    const result = mm.factory('empty', obj, null)
    expect(result).toBe(obj)
  })
})
