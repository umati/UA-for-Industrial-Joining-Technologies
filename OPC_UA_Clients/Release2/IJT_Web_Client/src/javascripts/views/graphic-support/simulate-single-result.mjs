export default class SimulateSingleResultInvoker {
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
      let methodData = this.methodManager.getMethod('SimulateSingleResult')
      if (!methodData) {
        const methodFolders = [
          [{ namespaceindex: this.addressSpace.nsTighteningServer, identifier: 'Simulations' },
            { namespaceindex: this.addressSpace.nsTighteningServer, identifier: 'SimulateResults' }]
        ]
        await this.methodManager.setupMethodsInFolders(methodFolders)
        methodData = this.methodManager.getMethod('SimulateSingleResult')
      }
      if (!methodData) {
        throw new Error('SimulateSingleResult method not available')
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

  async invoke (evaluationValue, includeTraces = false) {
    const methodData = this.simulateMethodData || await this.prepare()
    return this.methodManager.call(methodData, [
      { value: evaluationValue, type: { Identifier: '7' } },
      { value: includeTraces, type: { Identifier: '1' } }
    ])
  }
}
