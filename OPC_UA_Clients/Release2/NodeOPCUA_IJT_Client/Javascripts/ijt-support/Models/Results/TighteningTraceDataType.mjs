import IJTBaseModel from '../IJTBaseModel.mjs'

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
    return this.TraceId
  }

  getStepTrace (Id) {
    for (const step of this.StepTraces) {
      if (step.getIdentifier() === Id) {
        return step
      }
    }
    throw new Error('Could not find stepResult with Id: ' + Id)
  }

  // This sets up connection between a trace step and a result step
  createConnections (resultContent) {
    if (!this.StepTraces) {
      throw new Error('No steps in the trace')
    }
    for (const traceStep of this.StepTraces) {
      const resultStep = resultContent.getStep(traceStep.StepResultId)
      if (!resultStep) {
        return
      }
      traceStep.StepResultId = {
        type: 'linkedValue',
        value: traceStep.StepResultId,
        link: resultStep
      }
      resultStep.StepTraceId = {
        type: 'linkedValue',
        value: resultStep.StepTraceId,
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
