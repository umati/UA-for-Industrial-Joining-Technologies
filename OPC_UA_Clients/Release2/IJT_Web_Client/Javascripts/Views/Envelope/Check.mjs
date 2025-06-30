/**
 * Description placeholder
 *
 * @class Trigger
 * @typedef {Check}
 */
class Check {
  constructor (dimension) {
    this.dimension = dimension
  }

  violation (xValue, traces, polynomial) {
    return false
  }

  reset () {
    return -1
  }

  generateInputHTML (context, screen) {
    return screen.createArea('Check parameters')
  }
}

/**
 * Simple check that warns first time a value is over the limit
 *
 * @export
 * @class OverLimit
 * @typedef {OverLimit}
 * @extends {Check}
 *
export class OverLimit extends Check {
  static displayText = 'Over limit'

  violation (index, traces, xDimension, polynomial) {
    const xValue = traces[xDimension][index]
    const actualValue = traces[this.dimension][index]
    const limit = polynomial.value(xValue)
    if (limit < actualValue) {
      return {
        rangeName: xDimension,
        rangeValue: xValue,
        name: this.dimension,
        value: actualValue,
        limit,
        index
      }
    }
  }
}

/**
 * Simple check that warns first time a value is over the limit
 *
 * @export
 * @class UnderLimit
 * @typedef {OverLimit}
 * @extends {Check}
 *
export class UnderLimit extends Check {
  static displayText = 'Under limit'

  violation (index, traces, xDimension, polynomial) {
    const xValue = traces[xDimension][index]
    const actualValue = traces[this.dimension][index]
    const limit = polynomial.value(xValue)
    if (limit > actualValue) {
      return {
        rangeName: xDimension,
        rangeValue: xValue,
        name: this.dimension,
        value: actualValue,
        limit,
        index
      }
    }
  }
} */

/**
 * Checks that the value graph crosses the limit this number of times
 * Can be used for example to detect stickslip
 *
 * @export
 * @class Crossings
 * @typedef {Crossings}
 * @extends {Check}
 */
export class Crossings extends Check {
  static displayText = 'Crossings'

  constructor (dimension, crossings = 1) {
    super(dimension)
    this.crossings = crossings
    this.reset()
  }

  violation (index, traces, xDimension, polynomial) {
    const previousIndex = Math.max(0, index)
    const previousXValue = traces[xDimension][previousIndex]
    const xValue = traces[xDimension][index]
    const previousValue = traces[this.dimension][previousIndex]
    const actualValue = traces[this.dimension][index]
    const previousLimit = polynomial.value(previousXValue)
    const limit = polynomial.value(xValue)
    if ((previousLimit - previousValue) * (limit - actualValue) < 0) {
      if (!this.firstViolation) {
        this.firstViolation = {
          rangeName: xDimension,
          rangeValue: xValue,
          name: this.dimension,
          value: actualValue,
          limit,
          index
        }
      }
      if (this.violationNumber++ > this.crossings) {
        return this.firstViolation
      }
    }
  }

  reset () {
    this.violationNumber = 0
    this.firstViolation = null
    return 0
  }

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
      'Allowed Violations',
      screen.createInput('0', null, (value) => {
        this.firstViolation = value
      }),
      area
    )

    context.appendChild(area)
    return area
  }
}
