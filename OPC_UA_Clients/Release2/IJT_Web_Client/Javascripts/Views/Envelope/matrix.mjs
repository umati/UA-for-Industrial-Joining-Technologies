import MatrixInverter from './matrixInverse.mjs'

export default class Matrix {
  constructor (data) {
    this.matrix = data
    this.matrixInverter = new MatrixInverter()
  }

  multiply (matrix2) {
    const result = []
    const rows1 = this.matrix.length
    const cols1 = this.matrix[0].length
    const cols2 = matrix2.size()[1]

    for (let i = 0; i < rows1; i++) {
      result[i] = []
      for (let j = 0; j < cols2; j++) {
        let sum = 0
        for (let k = 0; k < cols1; k++) {
          sum += this.matrix[i][k] * matrix2.matrix[k][j]
        }
        result[i][j] = sum
      }
    }
    return new Matrix(result)
  }

  transpose () {
    const result = []
    for (let i = 0; i < this.matrix[0].length; i++) {
      const row = []
      for (let j = 0; j < this.matrix.length; j++) {
        row.push(this.matrix[j][i])
      }
      result.push(row)
    }
    return new Matrix(result)
  }

  size () {
    return [this.matrix.length, this.matrix[0].length]
  }

  subset (a, b = null) {
    if (b === null) {
      return new Matrix([this.matrix[a]])
    }
    return this.matrix[a][b]
  }

  determinant () {
    const n = this.matrix.length

    if (n === 1) {
      return this.matrix[0][0]
    }

    if (n === 2) {
      return this.matrix[0][0] * this.matrix[1][1] - this.matrix[0][1] * this.matrix[1][0]
    }

    let det = 0

    for (let i = 0; i < n; i++) {
      const subMatrix = this.matrix.slice(1).map(row => row.filter((_, j) => j !== i))
      det += ((i % 2 === 0 ? 1 : -1) * this.matrix[0][i] * subMatrix.determinant())
    }
    return det
  }

  /**
   * Inverse of a matrix. This was to complex to do for me so included
   * helpclass I modified from the web.
   *
   * @returns {Matrix} that is the inverse of the current matrix
   */
  inverse () {
    let stringMatrix = ''

    for (const row of this.matrix) {
      for (const element of row) {
        stringMatrix += element + ', '
      }
    }

    const m = this.matrixInverter.matInit(this.matrix.length, this.matrix[0].length, stringMatrix.substring(0, stringMatrix.length - 2))
    const inv = this.matrixInverter.matInverse(m)
    return new Matrix(inv)
  }
}
