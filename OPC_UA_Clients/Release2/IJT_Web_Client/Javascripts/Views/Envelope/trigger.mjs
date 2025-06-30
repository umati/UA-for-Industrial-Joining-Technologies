/**
 * Description placeholder
 *
 * @class Trigger
 * @typedef {Trigger}
 */
class Trigger {
  setValues (dimension, limitValue) {
    this.dimension = dimension
    this.limitValue = limitValue
  }

  check (value) {
    return false
  }

  firstTriggerIndex (result, simpleTrace) {
    return -1
  }

  generateInputHTML (context, screen) {
    return screen.createArea('Trigger parameters')
  }
}

class SimpleComparation extends Trigger {
  generateInputHTML (context, screen) {
    const area = super.generateInputHTML(context, screen)

    screen.createTitledInput(
      'Trace name',
      screen.createInput('TORQUE TRACE', null, (value) => {
        this.dimension = value
      }),
      area
    )

    screen.createTitledInput(
      'Limit value',
      screen.createInput('0', null, (value) => {
        this.limitValue = value
      }),
      area
    )

    context.appendChild(area)
    return area
  }
}

export class MoreThanEqualTrigger extends SimpleComparation {
  setValues (dimension, limitValue) {
    this.dimension = dimension
    this.limitValue = limitValue
  }

  check (checkvalue) {
    return checkvalue >= this.limitValue
  }

  static displayText = '>='

  firstTriggerIndex (result, simpleTrace) {
    const values = simpleTrace[this.dimension]
    let index = 0
    for (const value of values) {
      if (value >= this.limitValue) {
        return index
      }
      index++
    }
    return -1
  }
}

export class LessThanEqualTrigger extends SimpleComparation {
  setValues (dimension, limitValue) {
    this.dimension = dimension
    this.limitValue = limitValue
  }

  check (checkvalue) {
    return checkvalue >= this.limitValue
  }

  static displayText = '<='

  firstTriggerIndex (result, simpleTrace) {
    const values = simpleTrace[this.dimension]
    let index = 0
    for (const value of values) {
      if (value <= this.limitValue) {
        return index
      }
      index++
    }
    return -1
  }
}

export class StepTransition extends Trigger {
  setValues (step) {
    this.step = step
  }

  static displayText = 'Step'

  firstTriggerIndex (result, simpleTrace) {
    const stepTraces = result.ResultContent[0].Trace.StepTraces
    if (stepTraces.length < 1) {
      throw new Error('No steps in trace that is simplified')
    }
    let index = 0
    for (const stepTrace of stepTraces) {
      if (stepTrace === this.step || stepTrace.StepResultId.link === this.step || stepTrace.StepResultId.link.Name === this.step) {
        return index
      }
      index += stepTrace.StepTraceContent[0].Values.length
    }
  }

  generateInputHTML (context, screen) {
    const area = super.generateInputHTML(context, screen)

    screen.createTitledInput(
      'Step (Name or Id',
      screen.createInput('TightenToTorque_1', null, (value) => {
        this.step = value
      }),
      area
    )

    context.appendChild(area)
    return area
  }
}

export class StepResultValues extends Trigger {
  setValues (step, stepValueName) {
    this.step = step
    this.stepValueName = stepValueName
  }

  static displayText = 'Step value'

  /**
   * This trigger activates at a named value in a step.
   * TODO: This is not working since the tracepoint index is not sent in the result yet.
   *
   * @param {*} result
   * @param {*} simpleTrace
   * @returns {number}
   */
  firstTriggerIndex (result) {
    const stepTraces = result.ResultContent[0].Trace.StepTraces
    if (stepTraces.length < 1) {
      throw new Error('No steps in trace that is simplified')
    }
    let index = 0
    for (const stepTrace of stepTraces) {
      if (stepTrace === this.step || stepTrace.StepResultId.link === this.step || stepTrace.StepResultId.link.Name === this.step) {
        stepTrace.StepResultId.link.StepResultValues.forEach((value) => {
          if (value.Name === this.stepValueName) {
            return index + value.TracePointIndex
          }
        })
        return index
      }
      index += stepTrace.StepTraceContent[0].Values.length
    }
  }

  generateInputHTML (context, screen) {
    const area = super.generateInputHTML(context, screen)

    screen.createTitledInput(
      'Step (Name or Id)',
      screen.createInput('TightenToTorque_1', null, (value) => {
        this.step = value
      }),
      area
    )

    screen.createTitledInput(
      'Step value name',
      screen.createInput('Peak Torque', null, (value) => {
        this.stepValueName = value
      }),
      area
    )

    context.appendChild(area)
    return area
  }
}
