import IJTBaseModel from './IJTBaseModel.mjs'

// The purpose of this class is to represent the datastructure of a trace
// This datastructure stays true to the OPC UA IJT datamodel
// There is another datastructure for traces in the WebPage/Trace section
// That datastructure is aimed at displaying the trace on the screen uses this
// datamodel as input, via the createNewTrace(evt) event handler
export class TighteningTraceDataType extends IJTBaseModel {
  constructor (parameters, modelManager) {
    const castMapping = {
      steptraces: 'StepTraceDataType'
    }
    super(parameters, modelManager, castMapping)
  }

  getIdentifier () {
    return this.traceId
  }

  getStepTrace (Id) {
    for (const step of this.stepTraces) {
      if (step.getIdentifier() === Id) {
        return step
      }
    }
    throw new Error('Could not find stepResult with Id: ' + Id)
  }

  // This sets up connection between a trace step and a result step
  createConnections (resultContent) {
    if (!this.stepTraces) {
      throw new Error('No steps in the trace')
    }
    for (const traceStep of this.stepTraces) {
      const resultStep = resultContent.getStep(traceStep.stepResultId)
      if (!resultStep) {
        return
      }
      traceStep.stepResultId = {
        type: 'linkedValue',
        value: traceStep.stepResultId,
        link: resultStep
      }
      resultStep.stepTraceId = {
        type: 'linkedValue',
        value: resultStep.stepTraceId,
        link: traceStep
      }
    }
  }
}

// The purpose of this class is to
export class StepTraceDataType extends IJTBaseModel {
  constructor (parameters, modelManager) {
    const castMapping = {
      stepTraceContent: 'TraceContentDataType'
    }
    super(parameters, modelManager, castMapping)
  }

  getIdentifier () {
    return this.stepTraceId
  }
}

// The purpose of this class is to
export class TraceContentDataType extends IJTBaseModel {
}

// The purpose of this class is to
export class TraceValueDataType extends IJTBaseModel {
}
