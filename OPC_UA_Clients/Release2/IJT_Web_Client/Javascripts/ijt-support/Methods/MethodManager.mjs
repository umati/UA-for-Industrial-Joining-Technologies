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
            methodPromises.push(this.addressFolder(JSON.stringify(folderPath)))
          }

          this.methodObject = {}
          Promise.all(methodPromises).then((methodList) => {
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
  addressFolder (folderPath) {
    if (!folderPath || folderPath === '') {
      return this.folderPromise(this.tighteningSystemNode) // Automatically add all methods in the top folder (if path is empty)
    } else {
      return new Promise((resolve, reject) => {
        this.addressSpace.findNodeFromPathPromise(folderPath).then((folderNode) => {
          this.folderPromise(folderNode).then((folderPath) => {
            resolve(folderPath)
          })
        })
      })
    }
  }

  /**
   * Promise to set up a folder with all the method nodes.
   * @param {*} folderNode the node that contains methods
   * @returns  a Promise to setup all methods in a folder
   */
  folderPromise (folderNode) {
    return new Promise((resolve, reject) => {
      const methodPromises = []
      const relations = folderNode.getChildRelations('component')
      this.addressSpace.relationsToNodes(relations).then((children) => {
        for (const child of children) {
          if (child.nodeClass === '4') {
            methodPromises.push(this.setupMethod(child))
          }
        }
        Promise.all(methodPromises).then((methodList) => {
          for (const methodItem of methodList) {
            this.methodObject[methodItem.methodNode.displayName] = { parentNode: folderNode, methodNode: methodItem.methodNode, arguments: methodItem.arguments }
          }
          resolve()
        })
      })
    })
  }

  /**
   * Given a method node, set it up and sort out the data so thet it becomes easy to invoke (using the InputArguments children)
   * @param {*} methodNode
   * @returns a promise to load and setup the method data
   */
  setupMethod (methodNode) {
    return new Promise((resolve, reject) => {
      const allProperties = methodNode.getChildRelations('hasProperty')
      let inputArguments = allProperties.find(
        x => x.BrowseName.Name === 'InputArguments')
      if (!inputArguments) {
        inputArguments = []
      }
      this.addressSpace.relationsToNodes([inputArguments]).then((inputArgumentsNode) => {
        const simplifiedArguments = []
        for (const arg of inputArgumentsNode) {
          // console.log(arg)
          for (const argContent of arg.data.attributes.Value) {
            if (argContent) {
              // argContent.typeName = this.addressSpace.dataTypeEnumeration[argContent.dataType.split('=').pop()]
              simplifiedArguments.push(argContent)
            } else {
              console.log('Method arguments could not be found: ' + arg?.data?.value)
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
        switch (typeNr) {
          case '7': {
            castValue = parseInt(row.value)
            break
          }
          case '3': { // treat a byte as an int, for now
            castValue = parseInt(row.value)
            break
          }
          case '1': {
            castValue = row.value
            break
          }
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
