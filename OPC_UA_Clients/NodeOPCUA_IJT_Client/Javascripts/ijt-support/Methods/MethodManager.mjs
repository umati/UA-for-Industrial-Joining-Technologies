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
          for (const folder of methodFolders) {
            methodPromises.push(this.addressFolder(folder))
          }

          this.methodObject = {}
          Promise.all(methodPromises).then((methodList) => {
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
        this.addressSpace.findNodeFromPathPromise(`${folderPath}`).then((folderNode) => {
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
          if (child.data.nodeclass.value === 4) {
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
      const inputArgumets = allProperties.find(
        x => x.browseName.name === 'InputArguments')
      this.addressSpace.relationsToNodes([inputArgumets]).then((inputArgumentsNode) => {
        const simplifiedArguments = []
        for (const arg of inputArgumentsNode) {
          for (const argContent of arg?.data?.value?.message?.dataValue?.value?.value) {
            if (argContent) {
              argContent.typeName = this.addressSpace.dataTypeEnumeration[argContent.dataType.split('=').pop()]
              simplifiedArguments.push(argContent)
            } else {
              console.log('Method arguments could not be found: ' + arg?.data?.value?.message)
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
    const inputArguments = []
    for (const row of inputs) {
      let castValue
      const typeNr = row.type.split('=').pop()
      switch (typeNr) {
        case '7' : {
          castValue = parseInt(row.value)
          break
        }
        case '1' : {
          castValue = row.value
          break
        }
      }
      inputArguments.push({
        dataType: parseInt(typeNr),
        value: castValue
      })
    }

    this.addressSpace.methodCall(methodData.parentNode.nodeId, methodData.methodNode.nodeId, inputArguments).then(
      (results, err) => {
        if (err) {
          console.log(err)
        }
      }
    )
  }
}
