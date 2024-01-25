import { NodeFactory } from './Node.mjs'

export class AddressSpace {
  constructor (connectionManager) {
    this.connectionManager = connectionManager
    this.socketHandler = connectionManager.socketHandler
    this.nodeMapping = {}
    this.objectFolder = null
    this.listOfTSPromises = []
    this.newNodeSubscription = []
    this.status = []

    this.socketHandler.namespacePromise().then((namespaces) => {
      console.log(namespaces)
      this.handleNamespaces(namespaces.message)
      this.addressSpaceSetup('namespaces')
    })

    /* Listen to namespaces
    this.socketHandler.registerMandatory('namespaces', (msg) => {
      this.handleNamespaces(msg)
      this.addressSpaceSetup('namespaces')
    })

    // Listen to datatypes. Needed for method calls. SHOULD BE REMOVED???
    this.socketHandler.registerMandatory('datatypes', (msg) => {
      this.dataTypeEnumeration = msg.datatype
      this.addressSpaceSetup('datatypes')
    }) */

    this.connectionManager.subscribe('connection', (setToTrue) => {
      if (setToTrue) {
        this.initiate()
      }
    })
  }

  /**
   * Sets up root and the Object folder and find a Tightening System
   */
  initiate () {
    this.findOrLoadNode('ns=0;i=84').then((rootFolder) => { // GRoot
      this.findOrLoadNode('ns=0;i=85').then((objectFolder) => {
        this.objectFolder = objectFolder
        const typerelations = objectFolder.getTypeDefinitionRelations('1005')
        if (!typerelations || typerelations.length === 0) {
          throw new Error('Could not find Tightening System')
        }
        this.findOrLoadNode(typerelations[0].NodeId).then((tgtSystem) => {
          this.tighteningSystem = tgtSystem
          this.addressSpaceSetup('tighteningsystem')
          this.connectionManager.trigger('tighteningsystem', true)
          /* for (const promise of this.listOfTSPromises) {
            this.tighteningSystem = tgtSystem
            promise.resolve(tgtSystem)
          } */
        })
      })
    })
  }

  /**
   * Check that addressSpace has been set up and a tightening system exists
   * @returns true if the addressSpace is set up
   */
  addressSpaceCheck () {
    return this.status.find(x => x === 'tighteningsystem')
    // return this.status.find(x => x === 'namespaces') && this.status.find(x => x === 'datatypes') && this.status.find(x => x === 'tighteningsystem')
  }

  addressSpaceSetup (status) {
    this.status.push(status)
    if (this.addressSpaceCheck()) {
      for (const promise of this.listOfTSPromises) {
        promise.resolve(this.tighteningSystem)
      }
      this.listOfTSPromises = []
    }
  }

  /**
   * This returns a promise to get a fully set up address space system, including a loaded tightening system node, the namespace and the datatypes
   * Use this since the addressSpace might not be loaded yet
   * @returns a promise of a tightening system
   */
  addressSpacePromise () {
    return new Promise((resolve, reject) => {
      if (this.addressSpaceCheck()) { // Already fixed
        resolve(this.tighteningSystem)
        return
      }
      this.listOfTSPromises.push({ resolve, reject }) // Queue up and let them know later
    }
    )
  }

  methodCall (locationId, methodNode, args) {
    return new Promise((resolve, reject) => {
      this.socketHandler.methodCall(locationId, methodNode, args).then(
        (result) => {
          resolve(JSON.parse(result.message.output))
        },
        (error) => {
          reject(error)
        }
      )
    })
  }

  getIS (str) {
    if (Number(str)) {
      return ';i='
    }
    return ';s='
  }

  setNodeMapping (nodeId, newNode) {
    if (typeof nodeId === 'string' || nodeId instanceof String) {
      this.nodeMapping[nodeId] = newNode
    } else {
      this.nodeMapping['ns=' + nodeId.NamespaceIndex + this.getIS(nodeId.Identifier) + nodeId.Identifier] = newNode
    }
  }

  getNodeMapping (nodeId) {
    if (typeof nodeId === 'string' || nodeId instanceof String) {
      return this.nodeMapping[nodeId]
    } else {
      return this.nodeMapping['ns=' + nodeId.NamespaceIndex + this.getIS(nodeId.Identifier) + nodeId.Identifier]
    }
  }

  /**
  * This is the main promise for creating a node
  * @param {*} nodeId the node identity
  * @returns a Promise of a node
  */
  findOrLoadNode (nodeId) {
    /**
     * Supportfunction that takes the data from browseAndRead and turn it into an actual node
     * @param {*} nodeData the data from browseAndRead
     * @returns a node
     */
    const createNode = (nodeData) => {
      let newNode = this.getNodeMapping(nodeData.nodeid)

      if (!newNode) {
        newNode = NodeFactory(nodeData)
        this.setNodeMapping(newNode.nodeId, newNode)
      }

      for (const callback of this.newNodeSubscription) {
        callback(newNode)
      }
      return newNode
    }

    /**
     * This function is a promise to load the relevant data and then resolve a special structure that
     * can be set up to create a node. Most often loadAndCreate works better
     * @param {*} nodeId the node identity
     * @param {*} details do we want the extra data from the browse?
     * @returns a promise of a datastructure that can be used to create a node
     */
    const readAndStructure = (nodeId, details = false) => {
      return new Promise((resolve) => {
        this.socketHandler.readPromise(nodeId, 'DisplayName, NodeClass').then(
          (response) => {
            const attributes = JSON.parse(response.message.attributes.replace(/\n|\t/g, ''))
            const relations = JSON.parse(response.message.relations)
            const value = JSON.parse(response.message.value)
            const returnValue = {
              nodeid: response.message.nodeid,
              attributes,
              relations,
              value
            }
            resolve(returnValue)
          },
          (error) => {
            alert(error)
          })
      })
    }

    const returnNode = this.getNodeMapping(nodeId)
    if (returnNode) {
      return new Promise((resolve, reject) => {
        resolve(returnNode, false)
      })
    } else {
      return new Promise((resolve, reject) => {
        readAndStructure(nodeId, true).then((m) => {
          resolve(createNode(m), true)
        })
      })
    }
  }

  /**
   * This simplifies the use of the correct namespaces
   * @param {*} namespaces is the data sent bu the OPC UA client
   */
  handleNamespaces (namespaceMessage) {
    const namespaces = JSON.parse(namespaceMessage.namespaces)
    this.OPCUA = namespaces.indexOf('http://opcfoundation.org/UA/')
    this.nsIJT = namespaces.indexOf('http://opcfoundation.org/UA/IJT/Base/')
    this.nsTightening = namespaces.indexOf('http://opcfoundation.org/UA/IJT/Tightening/')
    this.nsTighteningServer = namespaces.indexOf('urn:AtlasCopco:IJT:Tightening:Server/')
    this.nsMachinery = namespaces.indexOf('http://opcfoundation.org/UA/Machinery/')
    this.nsMachineryResult = namespaces.indexOf('http://opcfoundation.org/UA/Machinery/Result/')
    this.nsDI = namespaces.indexOf('http://opcfoundation.org/UA/DI/')
    // this.nsIJTApplication = namespaces.indexOf('http://www.atlascopco.com/TighteningApplication/')
  }

  /**
   * Reset the mapping of nodeId to nodes
   */
  reset () {
    this.nodeMapping = {}
  }

  /**
   * Returns a promise to find the node at the relative path from the tightening system
   * @param {*} path The path from the tightening system
   * @returns the node at the paths end
   */
  findNodeFromPathPromise (path) {
    return new Promise((resolve, reject) =>
      this.addressSpacePromise().then((tgtSystem) => {
        this.socketHandler.pathtoidPromise(tgtSystem.nodeId, path).then(
          (msg) => { // Path node found
            this.findOrLoadNode(JSON.parse(msg.message.nodeid)).then(
              (node) => {
                resolve(node)
              },
              (fail) => {
                reject(fail)
              })
          },
          (error) => { // Path node not found
            reject(error)
          })
      })
    )
  }

  subscribeToNewNode (callback) {
    this.newNodeSubscription.push(callback)
  }

  /**
   * Turn a list of relations into a promise of a list of nodes
   * @param {*} relations a list of relations
   * @returns a Promise of a list of nodes
   */
  relationsToNodes (relations) {
    const promiseList = []
    // const nodeList = []
    for (const relation of relations) {
      promiseList.push(
        // this.findOrLoadNode(relation.nodeId)
        new Promise((resolve, reject) => {
          this.findOrLoadNode(relation.NodeId).then((node) => {
            resolve(node)
          })
        })
      )
    }

    return Promise.all(promiseList)
  }

  /**
   * Returns a promise to read an attribute in a node
   * @param {*} nodeId the node ID of the node that should be read
   * @param {*} attribute to be read
   * @returns a promise to return the attribute of the node
   */
  read (nodeId, attribute) {
    // console.log('SEND Read: '+this.nodeId)
    return new Promise((resolve) => {
      this.socketHandler.readPromise(nodeId, attribute).then(
        (response) => {
          resolve(response.node)
        },
        (error) => {
          alert(error)
        })
    })
  }
}
