const METHOD_NODE_CLASS = 4 // OPC UA NodeClass for Method nodes

export class MethodManager {
  constructor (addressSpace) {
    this.addressSpace = addressSpace
  }

  /**
   * This function takes a list of folders and search them for methods. Then getMethodNames(), getMethod(), and call() can be used to invoke them
   * @param {*} methodFolders a list of folders that should be searched for methods
   * @returns a Promise to load the methods in the list
   */
  setupMethodsInFolders (methodFolders) {
    return new Promise((resolve, reject) => {
      const methodPromises = []

      this.addressSpace.addressSpacePromise().then(
        (tighteningSystemNode) => {
          this.tighteningSystemNode = tighteningSystemNode
          for (const folderPath of methodFolders) {
            methodPromises.push(
              this.addressFolder(JSON.stringify(folderPath)).catch((error) => {
                console.warn('Skipping unavailable method folder', folderPath, error)
              })
            )
          }

          this.methodObject = {}
          Promise.all(methodPromises).then(() => {
            this.addressSpace.connectionManager.trigger('methods', true)
            resolve()
          })
        })
    })
  }

  /**
   * Support function that ensures that the containing folder is loaded
   * @param {*} folderPath the path to the folder. Remember to add the namespace number
   * @returns a Promise to setup all methods in a folder
   */
  async addressFolder (folderPath) {
    if (!folderPath || folderPath === '') {
      return this.folderPromise(this.tighteningSystemNode) // Automatically add all methods in the top folder (if path is empty)
    } else {
      const folderNode = await this.addressSpace.findNodeFromPathPromise(folderPath)
      return this.folderPromise(folderNode)
    }
  }

  /**
   * Promise to set up a folder with all the method nodes.
   * @param {*} folderNode the node that contains methods
   * @returns  a Promise to setup all methods in a folder
   */
  async folderPromise (folderNode) {
    const methodPromises = []
    const relations = folderNode.getChildRelations('component')
    const children = await this.addressSpace.relationsToNodes(relations)
    for (const child of children) {
      if (parseInt(child.nodeClass) === METHOD_NODE_CLASS) {
        methodPromises.push(this.setupMethod(child))
      }
    }
    const methodList = await Promise.all(methodPromises)
    for (const methodItem of methodList) {
      this.methodObject[methodItem.methodNode.displayName] = { parentNode: folderNode, methodNode: methodItem.methodNode, arguments: methodItem.arguments }
    }
  }

  /**
   * Given a method node, set it up and sort out the data so that it becomes
   * easy to invoke (using the InputArguments children).
   * @param {object} methodNode
   * @returns {Promise<{methodNode: object, arguments: object[]}>}
   */
  setupMethod (methodNode) {
    return new Promise((resolve, _reject) => {
      const allProperties = methodNode.getChildRelations('hasProperty')
      const inputArguments = allProperties.find(
        x => x.BrowseName.Name === 'InputArguments')

      const relationsPromise = inputArguments
        ? this.addressSpace.relationsToNodes([inputArguments])
        : Promise.resolve([])

      relationsPromise.then((inputArgumentsNode) => {
        const simplifiedArguments = []
        for (const arg of inputArgumentsNode) {
          for (const argContent of arg.data.attributes.Value) {
            if (argContent) {
              simplifiedArguments.push(argContent)
            } else {
              console.warn('Method arguments could not be found:', arg?.data?.value)
            }
          }
        }
        resolve({ methodNode, arguments: simplifiedArguments })
      })
    })
  }

  /**
   * Return a list of Method names
   * @returns
   */
  getMethodNames () {
    return Object.keys(this.methodObject)
  }

  /**
   * Given a method name, return data about the method
   * @param {*} name the name of the method
   * @returns
   */
  getMethod (name) {
    return this.methodObject[name]
  }

  /**
   * Invokes a method
   * @param {*} methodNode the method Node
   * @param {*} inputs the argument data
   */
  call (methodData, inputs) {
    return new Promise((resolve, reject) => {
      const inputArguments = []
      for (const row of inputs) {
        let castValue
        const typeNr = row.type.Identifier
        switch (parseInt(typeNr)) {
          case 3029: {
            castValue = row.value
            break
          }
          case 7: // UInt32
          case 8: // Int64
          case 9: // UInt64
          case 3: // Byte
          case 10: // Byte
          case 11: // Int32
          case 5: // Double
          case 4: // Float
            castValue = parseInt(row.value)
            break
          case 12: // String
          case 13: // DateTime
            castValue = String(row.value ?? '')
            break
          case 21: // LocalizedText — pass {Text, Locale} object through to Python
            castValue = row.value
            break
          case 1: // Boolean
            castValue = row.value === true || row.value === 'true'
            break
          default:
            castValue = row.value
        }
        inputArguments.push({
          dataType: parseInt(typeNr),
          value: castValue
        })
      }

      this.addressSpace.methodCall(methodData.parentNode.nodeId, methodData.methodNode.nodeId, inputArguments).then(
        (results) => {
          resolve(results)
        },
        (error) => {
          reject(error)
        }
      )
    })
  }
}
