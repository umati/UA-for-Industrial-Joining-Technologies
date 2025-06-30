/* jshint esversion:6 */

// import { math } from '../../../node_modules/mathjs/lib/browser/math.js'

// const { math } = require('mathjs')

import Matrix from './matrix.mjs'

export default class Polynomial {
  constructor (koefficients) {
    this.koefficients = koefficients
  }

  get degree () {
    return this.koefficients.length
  }

  get text () {
    function myToFixed (n) {
      const split = n.toString().split('e')

      if (!split || split.length !== 2) {
        return n
      }
      const k = split[0]
      const e = split[1]

      let sign = 1
      if (k < 0) {
        sign = -1
      }
      let kRest = k * sign

      if (Math.abs(n) < 1.0) {
        if (e) {
          kRest /= 10
          kRest = '0.' + (new Array(-e)).join('0') + kRest.toString().substring(2)
        }
      } else {
        kRest *= Math.pow(10, e)
      }
      if (sign < 0) {
        kRest = '-' + kRest
      }
      return kRest
    }

    let res = ''
    let power = this.koefficients.length - 1
    for (const a of this.koefficients) {
      res = res + ' ' + myToFixed(a) // math.round(a, 4)
      if (power === 1) {
        res = res + 'x_'
      } else if (power > 1) {
        res = res + 'x<sup>' + power + '</sup> '
      }
      power--
    }
    res += '__'
    return res
  }

  value (x) {
    let res = 0
    for (const a of this.koefficients) {
      res = res * x + parseFloat(a)
    }
    return res
  }
}

/**
 * This supportclass is intended to help move back and forth between a set of
 * (x, y) positions and a polynomial representation
 * It uses a least square method inspired by
 * http://mathworld.wolfram.com/LeastSquaresFittingPolynomial.html
 * (13)-(16)
 * */
export class PolynomialHandler {
  /**
   * @param {Object} xArray
   * @param {Object} degree
   * @return {Object}
   */

  /**
   *
   */
  calculateLeastSquaresPolynomial (xyvalues, degree) {
    function createXMatrix (xMatrix, degree) {
      let res = []
      for (let i = 0; i < xMatrix.size()[1]; i++) {
        let row = []
        const xi = xMatrix.subset(0, i)
        for (let j = 0; j < degree; j++) {
          row = [...row, Math.pow(xi, j)]
        }
        res = [...res, row]
      }
      return new Matrix(res)
    }

    const matrix = new Matrix(xyvalues)

    const x = matrix.subset(0)
    const y = matrix.subset(1)
    const xPowerMatrix = createXMatrix(x, degree + 1)

    const transpose = xPowerMatrix.transpose()
    const transPower = (transpose.multiply(xPowerMatrix).inverse()).multiply(transpose)
    const transY = y.transpose()
    const matrixAnswer = transPower.multiply(transY)

    const answerReverse = matrixAnswer.transpose()
    const answer = answerReverse.matrix[0].reverse()

    return new Polynomial(answer)
  }

  /**
   * @param {Array} constants
   * @param {number} start
   * @param {number} end
   * @param {number} nr
   * @return {Array}
   */
  generateMeasurements (constants, start, end, nr, padding = 0) {
    let returnXArray = []
    let returnYArray = []
    for (let i = start; i <= end + 0.001 + padding; i += (end - start) / (nr - 1)) {
      returnXArray = [...returnXArray, i - padding]
      returnYArray = [...returnYArray, this.value(i - padding, constants)]
    }
    // return math.matrix([returnXArray, returnYArray])
  }
}

/*
const v1 = [[1, 2, 3], [3, 2, 3]]

const ph = new PolynomialHandler()

const n = ph.calculateLeastSquaresPolynomial(v1, 2)
console.log(n.text)
*/
