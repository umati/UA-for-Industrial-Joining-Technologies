// Copied and modified from: https://jamesmccaffrey.wordpress.com/2020/04/24/matrix-inverse-with-javascript/
// mat_inv.js
// matrix inverse using Crout's decomposition

// Joakim: I reformed the code to my prefered style and encapsulated it in a class

export default class MatrixInverter {
  vecMake (n, val) {
    const result = []
    for (let i = 0; i < n; ++i) {
      result[i] = val
    }
    return result
  }

  matMake (rows, cols, val) {
    const result = []
    for (let i = 0; i < rows; ++i) {
      result[i] = []
      for (let j = 0; j < cols; ++j) {
        result[i][j] = val
      }
    }
    return result
  }

  matInit (rows, cols, s) {
    // ex: const m = matInit(2, 3, "1,2,3, 4,5,6");
    const result = this.matMake(rows, cols, 0.0)
    const vals = s.split(',')
    let k = 0
    for (let i = 0; i < rows; ++i) {
      for (let j = 0; j < cols; ++j) {
        result[i][j] = parseFloat(vals[k++])
      }
    }
    return result
  }

  matShow (m, dec, wid) {
    console.log(m)
  }

  matProduct (ma, mb) {
    const aRows = ma.length
    const aCols = ma[0].length
    const bRows = mb.length
    const bCols = mb[0].length
    if (aCols !== bRows) {
      throw Error('Non-conformable matrices')
    }

    const result = this.matMake(aRows, bCols, 0.0)

    for (let i = 0; i < aRows; ++i) { // each row of A
      for (let j = 0; j < bCols; ++j) { // each col of B
        for (let k = 0; k < aCols; ++k) { // could use bRows
          result[i][j] += ma[i][k] * mb[k][j]
        }
      }
    }

    return result
  }

  matInverse (m) {
    // assumes determinant is not 0
    // that is, the matrix does have an inverse
    const n = m.length
    const result = this.matMake(n, n, 0.0) // make a copy
    for (let i = 0; i < n; ++i) {
      for (let j = 0; j < n; ++j) {
        result[i][j] = m[i][j]
      }
    }

    const lum = this.matMake(n, n, 0.0) // combined lower & upper
    const perm = this.vecMake(n, 0.0) // out parameter
    this.matDecompose(m, lum, perm) // ignore return

    const b = this.vecMake(n, 0.0)
    for (let i = 0; i < n; ++i) {
      for (let j = 0; j < n; ++j) {
        if (i === perm[j]) {
          b[j] = 1.0
        } else {
          b[j] = 0.0
        }
      }

      const x = this.reduce(lum, b)
      for (let j = 0; j < n; ++j) {
        result[j][i] = x[j]
      }
    }
    return result
  }

  matDeterminant (m) {
    const n = m.length
    const lum = this.matMake(n, n, 0.0)
    const perm = this.vecMake(n, 0.0)
    let result = this.matDecompose(m, lum, perm) // -1 or +1
    for (let i = 0; i < n; ++i) {
      result *= lum[i][i]
    }
    return result
  }

  matDecompose (m, lum, perm) {
    // Crout's LU decomposition for matrix determinant and inverse
    // stores combined lower & upper in lum[][]
    // stores row permuations into perm[]
    // returns +1 or -1 according to even or odd perms
    // lower gets dummy 1.0s on diagonal (0.0s above)
    // upper gets lum values on diagonal (0.0s below)

    let toggle = +1 // even (+1) or odd (-1) row permutatuions
    const n = m.length

    // make a copy of m[][] into result lum[][]
    // lum = matMake(n, n, 0.0);
    for (let i = 0; i < n; ++i) {
      for (let j = 0; j < n; ++j) {
        lum[i][j] = m[i][j]
      }
    }

    // make perm[]
    // perm = vecMake(n, 0.0);
    for (let i = 0; i < n; ++i) {
      perm[i] = i
    }

    for (let j = 0; j < n - 1; ++j) { // note n-1
      let max = Math.abs(lum[j][j])
      let piv = j

      for (let i = j + 1; i < n; ++i) { // pivot index
        const xij = Math.abs(lum[i][j])
        if (xij > max) {
          max = xij
          piv = i
        }
      } // i

      if (piv !== j) {
        const tmp = lum[piv] // swap rows j, piv
        lum[piv] = lum[j]
        lum[j] = tmp

        const t = perm[piv] // swap perm elements
        perm[piv] = perm[j]
        perm[j] = t

        toggle = -toggle
      }

      const xjj = lum[j][j]
      if (xjj !== 0.0) { // TODO: fix bad compare here
        for (let i = j + 1; i < n; ++i) {
          const xij = lum[i][j] / xjj
          lum[i][j] = xij
          for (let k = j + 1; k < n; ++k) {
            lum[i][k] -= xij * lum[j][k]
          }
        }
      }
    } // j

    return toggle // for determinant
  } // matDecompose

  reduce (lum, b) {
    const n = lum.length
    const x = this.vecMake(n, 0.0)
    for (let i = 0; i < n; ++i) {
      x[i] = b[i]
    }

    for (let i = 1; i < n; ++i) {
      let sum = x[i]
      for (let j = 0; j < i; ++j) {
        sum -= lum[i][j] * x[j]
      }
      x[i] = sum
    }

    x[n - 1] /= lum[n - 1][n - 1]
    for (let i = n - 2; i >= 0; --i) {
      let sum = x[i]
      for (let j = i + 1; j < n; ++j) {
        sum -= lum[i][j] * x[j]
      }
      x[i] = sum / lum[i][i]
    }

    return x
  } // reduce
}

/*
console.log('Begin matrix inversion using JavaScript demo ')

const m = matInit(4, 4, '3,7,2,5,' +
  '4,0,1,1,' +
  '1,6,3,0,' +
  '2,8,4,3 ')

console.log('\nOriginal matrix m is: ')
matShow(m, 1, 5)

const d = matDeterminant(m)
console.log('\nDeterminant of m = ')
console.log(d)

const inv = matInverse(m)
console.log('\nInverse of m is: ')
matShow(inv, 4, 8)

const check = matProduct(m, inv)
console.log('\nProduct of m * inv is: ')
matShow(check, 2, 7)

console.log('\nEnd demo')
*/
