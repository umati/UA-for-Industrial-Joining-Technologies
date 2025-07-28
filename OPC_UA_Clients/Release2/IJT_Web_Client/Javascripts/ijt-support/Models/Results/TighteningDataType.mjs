import ResultDataType from './ResultDataType.mjs'
// The purpose of this class is to handle the actual subscription or reading of a value and via socketIO send the result to the webpage
export default class TighteningDataType extends ResultDataType {
  constructor (parameters, modelManager) {
    let simplifiedParameters
    if (parameters.Value) {
      simplifiedParameters = {
        ResultMetaData: parameters.Value.ResultMetaData,
        ResultContent: parameters.Value.ResultContent
      }
    } else {
      simplifiedParameters = {
        ResultMetaData: parameters.ResultMetaData,
        ResultContent: parameters.ResultContent
      }
    }
    const castMapping = {
      ResultContent: 'JoiningResultDataType'
    }
    super(simplifiedParameters, modelManager, castMapping)

    this.consolidatedResultType = 'Joining'

    if (this.ResultContent[0]?.Trace) {
      this.ResultContent[0].Trace.createConnections(this)
    }
  }

  getStep (Id) {
    if (!this.ResultContent[0].StepResults || this.ResultContent[0].StepResults.length < 1) {
      throw new Error('Could not find stepResult with Id: ' + Id)
    }
    for (const step of this.ResultContent[0].StepResults) {
      if (step.getIdentifier() === Id) {
        return step
      }
    }
    // throw new Error('Could not find stepResult with Id: '+Id);
  }

  /**
   * Combines all trace points from all steps and add adds a 'TimeTrace' list
   *
   * @returns an object where each property represents the tracepoints for each reported dimension
   */
  simplifyAllTracePoints () {
    if (this.ResultContent.length < 1) {
      throw new Error('No content in result that is simplified')
    }
    const stepTraces = this.ResultContent[0].Trace.StepTraces
    if (stepTraces.length < 1) {
      throw new Error('No steps in trace that is simplified')
    }
    const pointList = { 'TIME TRACE': [] }
    for (const c of stepTraces[0].StepTraceContent) {
      pointList[c.Name] = []
    }
    for (const stepTrace of stepTraces) {
      for (const c of stepTrace.StepTraceContent) {
        pointList[c.Name] = [...pointList[c.Name], ...c.Values.map(parseFloat)]
      }
      for (let index = 0; index < stepTrace.StepTraceContent[0].Values.length; index++) {
        pointList['TIME TRACE'].push(index * parseFloat(stepTrace.SamplingInterval) + parseFloat(stepTrace.StartTimeOffset))
      }
    }
    return pointList
  }

  simplifiedTraceToStepAndIndex (totalIndex) {
    let remaining = totalIndex
    for (const stepTrace of this.ResultContent[0].Trace.StepTraces) {
      if (stepTrace.StepTraceContent[0].Values.length < remaining) {
        remaining -= stepTrace.StepTraceContent[0].Values.length
      } else {
        return {
          step: stepTrace.StepResultId.link,
          steptrace: stepTrace,
          index: remaining
        }
      }
    }
  }
}
