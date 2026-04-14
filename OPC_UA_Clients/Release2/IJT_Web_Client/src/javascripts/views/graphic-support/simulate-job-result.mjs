function defaultValueForArgument (arg) {
  const name = String(arg?.Name || '').toLowerCase()
  const dataType = arg?.DataType || { Identifier: '12' }
  const identifier = String(dataType.Identifier || '')

  if (name.includes('classification')) {
    // JOB classification (ResultClassification enum)
    return { value: 4, type: dataType }
  }
  if (name.includes('result type')) {
    return { value: 2, type: dataType }
  }
  if (name.includes('include traces')) {
    return { value: true, type: dataType }
  }
  if (name.includes('number of results')) {
    return { value: 1, type: dataType }
  }
  if (name.includes('duration between results')) {
    return { value: 100, type: dataType }
  }
  if (name.includes('update result variables')) {
    return { value: true, type: dataType }
  }
  if (name.includes('from sequence number')) {
    return { value: 1, type: dataType }
  }
  if (name.includes('to sequence number')) {
    return { value: 1, type: dataType }
  }

  if (identifier === '1') {
    return { value: true, type: dataType }
  }
  if (identifier === '21') {
    return { value: { Locale: '', Text: '' }, type: dataType }
  }
  if (['4', '5', '6', '7', '8', '10', '11'].includes(identifier)) {
    return { value: 0, type: dataType }
  }
  return { value: '', type: dataType }
}

export default class SimulateJobResultInvoker {
  constructor (methodManager, addressSpace) {
    this.methodManager = methodManager
    this.addressSpace = addressSpace
    this.simulateMethodData = null
    this.preparingPromise = null
  }

  async prepare () {
    if (this.simulateMethodData) {
      return this.simulateMethodData
    }
    if (this.preparingPromise) {
      return this.preparingPromise
    }

    this.preparingPromise = (async () => {
      const resolveMethod = () =>
        this.methodManager.getMethod('SimulateJobResult') ||
        this.methodManager.getMethod('SimulateBatch_Or_Sync_Result')

      let methodData = resolveMethod()
      if (!methodData) {
        const methodFolders = [[
          { namespaceindex: this.addressSpace.nsTighteningServer, identifier: 'Simulations' },
          { namespaceindex: this.addressSpace.nsTighteningServer, identifier: 'SimulateResults' }
        ]]
        await this.methodManager.setupMethodsInFolders(methodFolders)
        methodData = resolveMethod()
      }

      if (!methodData) {
        throw new Error('No job simulation method available (expected SimulateJobResult or SimulateBatch_Or_Sync_Result)')
      }

      this.simulateMethodData = methodData
      return methodData
    })()

    try {
      return await this.preparingPromise
    } finally {
      this.preparingPromise = null
    }
  }

  async invoke () {
    const methodData = this.simulateMethodData || await this.prepare()
    const args = (Array.isArray(methodData?.arguments) ? methodData.arguments : []).map((arg) => defaultValueForArgument(arg))
    return this.methodManager.call(methodData, args)
  }
}
