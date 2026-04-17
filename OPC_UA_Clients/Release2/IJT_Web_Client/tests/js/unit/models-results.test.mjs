/**
 * Unit tests for models/results/*.mjs data types.
 *
 * Uses the real ModelManager (with stubbed entity/joint managers) so that
 * the factory cast-mapping logic is also exercised.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ModelManager } from '../../../src/javascripts/ijt-support/models/model-manager.mjs'
import ResultDataType from '../../../src/javascripts/ijt-support/models/results/result-data-type.mjs'
import JoiningResultDataType from '../../../src/javascripts/ijt-support/models/results/joining-result-data-type.mjs'
import ResultValueDataType from '../../../src/javascripts/ijt-support/models/results/result-value-data-type.mjs'
import StepResultDataType from '../../../src/javascripts/ijt-support/models/results/step-result-data-type.mjs'
import BatchDataModel from '../../../src/javascripts/ijt-support/models/results/batch-data-type.mjs'
import JobDataModel from '../../../src/javascripts/ijt-support/models/results/job-data-model.mjs'
import ResultMetaData from '../../../src/javascripts/ijt-support/models/results/result-meta-data.mjs'
import ResultCounters from '../../../src/javascripts/ijt-support/models/results/result-counters.mjs'
import TighteningDataType from '../../../src/javascripts/ijt-support/models/results/tightening-data-type.mjs'
import { TighteningTraceDataType, StepTraceDataType, TraceContentDataType, TraceValueDataType } from '../../../src/javascripts/ijt-support/models/results/tightening-trace-data-type.mjs'

// ---------------------------------------------------------------------------
// Shared model manager factory
// ---------------------------------------------------------------------------

function makeMM () {
  return new ModelManager(
    { addEntity: vi.fn() },
    { addEntity: vi.fn() }
  )
}

// ---------------------------------------------------------------------------
// ResultValueDataType
// ---------------------------------------------------------------------------

describe('ResultValueDataType', () => {
  it('constructs from parameters', () => {
    const mm = makeMM()
    const rv = new ResultValueDataType({ ValueTag: '5', Value: '10.5' }, mm)
    expect(rv.ValueTag).toBe('5')
    expect(rv.Value).toBe('10.5')
  })

  it('handles empty parameters', () => {
    const mm = makeMM()
    const rv = new ResultValueDataType({}, mm)
    expect(rv).toBeDefined()
  })
})

// ---------------------------------------------------------------------------
// StepResultDataType
// ---------------------------------------------------------------------------

describe('StepResultDataType', () => {
  it('constructs and exposes StepResultId', () => {
    const mm = makeMM()
    const step = new StepResultDataType({ StepResultId: 'step-1', StepType: 2 }, mm)
    expect(step.StepResultId).toBe('step-1')
    expect(step.StepType).toBe(2)
  })

  it('getIdentifier returns StepResultId', () => {
    const mm = makeMM()
    const step = new StepResultDataType({ StepResultId: 'step-42' }, mm)
    expect(step.getIdentifier()).toBe('step-42')
  })

  it('getIdentifier returns undefined when StepResultId is absent', () => {
    const mm = makeMM()
    const step = new StepResultDataType({}, mm)
    expect(step.getIdentifier()).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// ResultMetaData
// ---------------------------------------------------------------------------

describe('ResultMetaData', () => {
  it('constructs with basic properties', () => {
    const mm = makeMM()
    const rmd = new ResultMetaData({ ResultId: 'r1', Name: 'Test', Classification: '1' }, mm)
    expect(rmd.ResultId).toBe('r1')
    expect(rmd.Name).toBe('Test')
    expect(rmd.Classification).toBe('1')
  })

  it('normalises missing AssociatedEntities to empty array', () => {
    const mm = makeMM()
    const rmd = new ResultMetaData({ ResultId: 'r1' }, mm)
    expect(rmd.AssociatedEntities).toEqual([])
  })

  it('normalises single AssociatedEntities object to array', () => {
    const mm = makeMM()
    const rmd = new ResultMetaData({
      ResultId: 'r1',
      AssociatedEntities: { Name: 'Tool1', EntityId: 'T1', EntityType: 4 }
    }, mm)
    expect(Array.isArray(rmd.AssociatedEntities)).toBe(true)
    expect(rmd.AssociatedEntities).toHaveLength(1)
  })

  it('keeps AssociatedEntities as array when already an array', () => {
    const mm = makeMM()
    const rmd = new ResultMetaData({
      ResultId: 'r1',
      AssociatedEntities: [
        { Name: 'Tool1', EntityId: 'T1', EntityType: 4 },
        { Name: 'Tool2', EntityId: 'T2', EntityType: 4 }
      ]
    }, mm)
    expect(rmd.AssociatedEntities).toHaveLength(2)
  })
})

// ---------------------------------------------------------------------------
// ResultCounters
// ---------------------------------------------------------------------------

describe('ResultCounters', () => {
  it('constructs with counter properties', () => {
    const mm = makeMM()
    const rc = new ResultCounters({ NOKCount: 3, OKCount: 10 }, mm)
    expect(rc.NOKCount).toBe(3)
    expect(rc.OKCount).toBe(10)
  })

  it('handles empty parameters', () => {
    const mm = makeMM()
    const rc = new ResultCounters({}, mm)
    expect(rc).toBeDefined()
  })
})

// ---------------------------------------------------------------------------
// ResultDataType
// ---------------------------------------------------------------------------

describe('ResultDataType', () => {
  it('constructs and initialises ClientData.rebuildState', () => {
    const mm = makeMM()
    const r = new ResultDataType({ ResultMetaData: { ResultId: 'r1', Name: 'R' } }, mm)
    expect(r.ClientData.rebuildState.claimed).toBe(false)
    expect(r.ClientData.rebuildState.resolved).toBe(false)
    expect(r.ClientData.rebuildState.partial).toBe(false)
  })

  it('unwraps Value wrapper when present', () => {
    const mm = makeMM()
    const r = new ResultDataType({
      Value: { ResultMetaData: { ResultId: 'wrapped', Name: 'W' } }
    }, mm)
    expect(r.ResultMetaData).toBeDefined()
  })

  it('id getter returns ResultMetaData.ResultId', () => {
    const mm = makeMM()
    const r = new ResultDataType({ ResultMetaData: { ResultId: 'id-1', Name: 'Test' } }, mm)
    expect(r.id).toBe('id-1')
  })

  it('name getter returns ResultMetaData.Name', () => {
    const mm = makeMM()
    const r = new ResultDataType({ ResultMetaData: { ResultId: 'r1', Name: 'MyResult' } }, mm)
    expect(r.name).toBe('MyResult')
  })

  it('classification getter returns ResultMetaData.Classification', () => {
    const mm = makeMM()
    const r = new ResultDataType({ ResultMetaData: { ResultId: 'r1', Classification: '2' } }, mm)
    expect(r.classification).toBe('2')
  })

  it('isPartial returns true when IsPartial is "True"', () => {
    const mm = makeMM()
    const r = new ResultDataType({ ResultMetaData: { ResultId: 'r1', IsPartial: 'True' } }, mm)
    expect(r.isPartial).toBe(true)
  })

  it('isPartial returns false when IsPartial is "False"', () => {
    const mm = makeMM()
    const r = new ResultDataType({ ResultMetaData: { ResultId: 'r1', IsPartial: 'False' } }, mm)
    expect(r.isPartial).toBe(false)
  })

  it('evaluation returns true when ResultEvaluation is OK enum string', () => {
    const mm = makeMM()
    const r = new ResultDataType({ ResultMetaData: { ResultId: 'r1', ResultEvaluation: 'ResultEvaluationEnum.OK' } }, mm)
    expect(r.evaluation).toBe(true)
  })

  it('evaluation returns true when ResultEvaluation is 1', () => {
    const mm = makeMM()
    const r = new ResultDataType({ ResultMetaData: { ResultId: 'r1', ResultEvaluation: 1 } }, mm)
    expect(r.evaluation).toBe(true)
  })

  it('evaluation returns false for non-OK evaluation', () => {
    const mm = makeMM()
    const r = new ResultDataType({ ResultMetaData: { ResultId: 'r1', ResultEvaluation: 2 } }, mm)
    expect(r.evaluation).toBe(false)
  })

  it('time returns EndTime when ProcessingTimes.EndTime is set', () => {
    const mm = makeMM()
    const r = new ResultDataType({
      ResultMetaData: {
        ResultId: 'r1',
        ProcessingTimes: { EndTime: '2024-01-01T00:00:00Z' }
      }
    }, mm)
    expect(r.time).toBe('2024-01-01T00:00:00Z')
  })

  it('time returns "No Time" when ProcessingTimes.EndTime is absent', () => {
    const mm = makeMM()
    const r = new ResultDataType({ ResultMetaData: { ResultId: 'r1' } }, mm)
    expect(r.time).toBe('No Time')
  })

  it('isReference returns true when CreationTime is absent', () => {
    const mm = makeMM()
    const r = new ResultDataType({ ResultMetaData: { ResultId: 'r1' } }, mm)
    expect(r.isReference).toBe(true)
  })

  it('isReference returns false when CreationTime is present', () => {
    const mm = makeMM()
    const r = new ResultDataType({ ResultMetaData: { ResultId: 'r1', CreationTime: '2024-01-01' } }, mm)
    expect(r.isReference).toBe(false)
  })

  it('replaceReference swaps the child at the correct index', () => {
    const mm = makeMM()
    const r = new ResultDataType({ ResultMetaData: { ResultId: 'r1' } }, mm)
    const arr = ['a', 'b', 'c']
    r.replaceReference('b', 'X', arr)
    expect(arr).toEqual(['a', 'X', 'c'])
  })
})

// ---------------------------------------------------------------------------
// JoiningResultDataType
// ---------------------------------------------------------------------------

describe('JoiningResultDataType', () => {
  it('constructs and initialises ClientData.rebuildState', () => {
    const mm = makeMM()
    const jr = new JoiningResultDataType({ OverallResultValues: [], StepResults: [] }, mm)
    expect(jr.ClientData.rebuildState.claimed).toBe(false)
  })

  it('unwraps Value wrapper', () => {
    const mm = makeMM()
    const jr = new JoiningResultDataType({
      Value: { OverallResultValues: [], StepResults: [] }
    }, mm)
    expect(jr).toBeDefined()
  })

  it('isReference returns true when ResultMetaData has no CreationTime', () => {
    const mm = makeMM()
    const jr = new JoiningResultDataType({ ResultMetaData: { ResultId: 'r1' } }, mm)
    expect(jr.isReference).toBe(true)
  })

  it('isReference returns false when ResultMetaData has CreationTime', () => {
    const mm = makeMM()
    const jr = new JoiningResultDataType({ ResultMetaData: { ResultId: 'r1', CreationTime: '2024' } }, mm)
    expect(jr.isReference).toBe(false)
  })

  it('isReference returns false when ResultMetaData is absent', () => {
    const mm = makeMM()
    const jr = new JoiningResultDataType({}, mm)
    expect(jr.isReference).toBeFalsy()
  })

  it('getTaggedValues throws when StepResults is empty', () => {
    const mm = makeMM()
    const jr = new JoiningResultDataType({ StepResults: [] }, mm)
    expect(() => jr.getTaggedValues(5)).toThrow()
  })

  it('getTaggedValues returns values matching the tag', () => {
    const mm = makeMM()
    const jr = new JoiningResultDataType({ StepResults: [] }, mm)
    // Manually inject StepResults since constructor normalises them
    jr.StepResults = [
      { StepResultValues: [{ ValueTag: '5', Value: 1 }, { ValueTag: '6', Value: 2 }] },
      { StepResultValues: [{ ValueTag: '5', Value: 3 }] }
    ]
    const tagged = jr.getTaggedValues(5)
    expect(tagged).toHaveLength(2)
    expect(tagged[0].ValueTag).toBe('5')
  })

  it('getTaggedValues returns empty array when no values match', () => {
    const mm = makeMM()
    const jr = new JoiningResultDataType({}, mm)
    jr.StepResults = [
      { StepResultValues: [{ ValueTag: '3', Value: 1 }] }
    ]
    const tagged = jr.getTaggedValues(9)
    expect(tagged).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// BatchDataModel
// ---------------------------------------------------------------------------

describe('BatchDataModel', () => {
  it('constructs and sets consolidatedResultType to "Batch"', () => {
    const mm = makeMM()
    const b = new BatchDataModel({ ResultMetaData: { ResultId: 'b1', Name: 'Batch' } }, mm)
    expect(b.consolidatedResultType).toBe('Batch')
  })

  it('inherits id getter from ResultDataType', () => {
    const mm = makeMM()
    const b = new BatchDataModel({ ResultMetaData: { ResultId: 'batch-99' } }, mm)
    expect(b.id).toBe('batch-99')
  })
})

// ---------------------------------------------------------------------------
// JobDataModel
// ---------------------------------------------------------------------------

describe('JobDataModel', () => {
  it('constructs and sets consolidatedResultType to "Job"', () => {
    const mm = makeMM()
    const j = new JobDataModel({ ResultMetaData: { ResultId: 'j1', Name: 'Job' } }, mm)
    expect(j.consolidatedResultType).toBe('Job')
  })

  it('inherits id getter from ResultDataType', () => {
    const mm = makeMM()
    const j = new JobDataModel({ ResultMetaData: { ResultId: 'job-7' } }, mm)
    expect(j.id).toBe('job-7')
  })
})

// ---------------------------------------------------------------------------
// TighteningTraceDataType
// ---------------------------------------------------------------------------

describe('TighteningTraceDataType', () => {
  it('constructs with TraceId', () => {
    const mm = makeMM()
    const trace = new TighteningTraceDataType({ TraceId: 'trace-1' }, mm)
    expect(trace.getIdentifier()).toBe('trace-1')
  })

  it('getStepTrace throws when stepTrace with given Id is not found', () => {
    const mm = makeMM()
    const trace = new TighteningTraceDataType({ TraceId: 'trace-1' }, mm)
    trace.StepTraces = [{ getIdentifier: () => 'step-1', StepResultId: 'step-1' }]
    expect(() => trace.getStepTrace('nonexistent')).toThrow()
  })

  it('getStepTrace returns the matching step trace', () => {
    const mm = makeMM()
    const trace = new TighteningTraceDataType({ TraceId: 'trace-1' }, mm)
    const step = { getIdentifier: () => 'step-1', StepResultId: 'step-1' }
    trace.StepTraces = [step]
    expect(trace.getStepTrace('step-1')).toBe(step)
  })

  it('createConnections throws when StepTraces is absent', () => {
    const mm = makeMM()
    const trace = new TighteningTraceDataType({ TraceId: 'trace-1' }, mm)
    expect(() => trace.createConnections({})).toThrow('No steps in the trace')
  })

  it('createConnections returns early when resultContent.getStep returns undefined', () => {
    const mm = makeMM()
    const trace = new TighteningTraceDataType({ TraceId: 'trace-1' }, mm)
    trace.StepTraces = [{ StepResultId: 'step-1' }]
    const resultContent = { getStep: () => undefined }
    expect(() => trace.createConnections(resultContent)).not.toThrow()
  })

  it('createConnections links trace step and result step', () => {
    const mm = makeMM()
    const trace = new TighteningTraceDataType({ TraceId: 'trace-1' }, mm)
    const traceStep = { StepResultId: 'step-1', StepTraceId: 'trace-step-1' }
    trace.StepTraces = [traceStep]
    const resultStep = { StepResultId: 'step-1', StepTraceId: 'trace-step-1' }
    const resultContent = { getStep: (_id) => resultStep }
    trace.createConnections(resultContent)
    expect(traceStep.StepResultId.type).toBe('linkedValue')
    expect(traceStep.StepResultId.link).toBe(resultStep)
  })
})

// ---------------------------------------------------------------------------
// StepTraceDataType
// ---------------------------------------------------------------------------

describe('StepTraceDataType', () => {
  it('constructs with basic properties', () => {
    const mm = makeMM()
    const st = new StepTraceDataType({ stepTraceId: 'st-1', SamplingInterval: '0.01' }, mm)
    expect(st.SamplingInterval).toBe('0.01')
  })

  it('getIdentifier returns stepTraceId', () => {
    const mm = makeMM()
    const st = new StepTraceDataType({ stepTraceId: 'st-1' }, mm)
    expect(st.getIdentifier()).toBe('st-1')
  })
})

// ---------------------------------------------------------------------------
// TraceContentDataType
// ---------------------------------------------------------------------------

describe('TraceContentDataType', () => {
  it('constructs with Name and Values', () => {
    const mm = makeMM()
    const tc = new TraceContentDataType({ Name: 'Torque', Values: ['1.0', '2.0', '3.0'] }, mm)
    expect(tc.Name).toBe('Torque')
  })
})

// ---------------------------------------------------------------------------
// TraceValueDataType
// ---------------------------------------------------------------------------

describe('TraceValueDataType', () => {
  it('constructs with given parameters', () => {
    const mm = makeMM()
    const tv = new TraceValueDataType({ Value: '5.5', Unit: 'Nm' }, mm)
    expect(tv.Value).toBe('5.5')
    expect(tv.Unit).toBe('Nm')
  })
})

// ---------------------------------------------------------------------------
// TighteningDataType
// ---------------------------------------------------------------------------

describe('TighteningDataType — constructor', () => {
  it('constructs without Value wrapper and sets consolidatedResultType', () => {
    const mm = makeMM()
    const t = new TighteningDataType({
      ResultMetaData: { ResultId: 'r1', Classification: '1' },
      ResultContent: []
    }, mm)
    expect(t.consolidatedResultType).toBe('Joining')
  })

  it('constructs with Value wrapper — unwraps parameters', () => {
    const mm = makeMM()
    const t = new TighteningDataType({
      Value: {
        ResultMetaData: { ResultId: 'r2', Name: 'Wrapped', Classification: '1' },
        ResultContent: []
      }
    }, mm)
    expect(t.consolidatedResultType).toBe('Joining')
  })

  it('does not crash when ResultContent is empty (no Trace)', () => {
    const mm = makeMM()
    expect(() => new TighteningDataType({
      ResultMetaData: { ResultId: 'r3' },
      ResultContent: []
    }, mm)).not.toThrow()
  })
})

describe('TighteningDataType — getStep', () => {
  it('throws when StepResults is empty', () => {
    const mm = makeMM()
    const t = new TighteningDataType({ ResultMetaData: { ResultId: 'r1' }, ResultContent: [] }, mm)
    t.ResultContent = [{ StepResults: [] }]
    expect(() => t.getStep('step-1')).toThrow()
  })

  it('returns the matching step by identifier', () => {
    const mm = makeMM()
    const t = new TighteningDataType({ ResultMetaData: { ResultId: 'r1' }, ResultContent: [] }, mm)
    const step = { getIdentifier: () => 'step-5' }
    t.ResultContent = [{ StepResults: [step] }]
    expect(t.getStep('step-5')).toBe(step)
  })

  it('returns undefined when step is not found', () => {
    const mm = makeMM()
    const t = new TighteningDataType({ ResultMetaData: { ResultId: 'r1' }, ResultContent: [] }, mm)
    const step = { getIdentifier: () => 'step-1' }
    t.ResultContent = [{ StepResults: [step] }]
    expect(t.getStep('nonexistent')).toBeUndefined()
  })
})

describe('TighteningDataType — simplifyAllTracePoints', () => {
  function makeTighteningWithTrace () {
    const mm = makeMM()
    const t = new TighteningDataType({ ResultMetaData: { ResultId: 'r1' }, ResultContent: [] }, mm)
    const stepTrace = {
      SamplingInterval: '0.01',
      StartTimeOffset: '0',
      StepTraceContent: [
        { Name: 'Torque', Values: ['1.0', '2.0', '3.0'] },
        { Name: 'Angle', Values: ['10', '20', '30'] }
      ]
    }
    t.ResultContent = [{
      Trace: { StepTraces: [stepTrace] }
    }]
    return t
  }

  it('throws when ResultContent is empty', () => {
    const mm = makeMM()
    const t = new TighteningDataType({ ResultMetaData: { ResultId: 'r1' }, ResultContent: [] }, mm)
    t.ResultContent = []
    expect(() => t.simplifyAllTracePoints()).toThrow('No content in result')
  })

  it('throws when StepTraces is empty', () => {
    const mm = makeMM()
    const t = new TighteningDataType({ ResultMetaData: { ResultId: 'r1' }, ResultContent: [] }, mm)
    t.ResultContent = [{ Trace: { StepTraces: [] } }]
    expect(() => t.simplifyAllTracePoints()).toThrow('No steps in trace')
  })

  it('returns a point list with TIME TRACE and named channels', () => {
    const t = makeTighteningWithTrace()
    const result = t.simplifyAllTracePoints()
    expect(result['TIME TRACE']).toHaveLength(3)
    expect(result['Torque']).toEqual([1, 2, 3])
    expect(result['Angle']).toEqual([10, 20, 30])
  })
})

describe('TighteningDataType — simplifiedTraceToStepAndIndex', () => {
  it('returns step/steptrace/index when remaining falls within a step', () => {
    const mm = makeMM()
    const t = new TighteningDataType({ ResultMetaData: { ResultId: 'r1' }, ResultContent: [] }, mm)
    const resultStep = { StepResultId: 'step-1' }
    const traceStep = {
      StepResultId: { link: resultStep },
      StepTraceContent: [{ Values: ['1', '2', '3', '4', '5'] }]
    }
    t.ResultContent = [{ Trace: { StepTraces: [traceStep] } }]
    const res = t.simplifiedTraceToStepAndIndex(3)
    expect(res.step).toBe(resultStep)
    expect(res.index).toBe(3)
  })

  it('skips steps where remaining exceeds the step length', () => {
    const mm = makeMM()
    const t = new TighteningDataType({ ResultMetaData: { ResultId: 'r1' }, ResultContent: [] }, mm)
    const resultStep2 = { StepResultId: 'step-2' }
    const traceStep1 = {
      StepResultId: { link: { StepResultId: 'step-1' } },
      StepTraceContent: [{ Values: ['1', '2', '3'] }]
    }
    const traceStep2 = {
      StepResultId: { link: resultStep2 },
      StepTraceContent: [{ Values: ['4', '5', '6'] }]
    }
    t.ResultContent = [{ Trace: { StepTraces: [traceStep1, traceStep2] } }]
    const res = t.simplifiedTraceToStepAndIndex(5)
    expect(res.step).toBe(resultStep2)
    expect(res.index).toBe(2)
  })
})
