import { NodeFactory } from './node.mjs'
import { ijtLog } from '../ijt-logger.mjs'

export class AddressSpace {
  constructor (connectionManager) {
    this.connectionManager = connectionManager
    this.socketHandler = connectionManager.socketHandler
    this.nodeMapping = {}
    this.objectFolder = null
    this.listOfTSPromises = []
    this.newNodeSubscription = []
    this.status = []

    this.connectionManager.subscribe('connection', (setToTrue) => {
      if (setToTrue) {
        this.initiate()
      }

      this.socketHandler.namespacePromise().then((namespaces) => {
        // console.log(namespaces)
        this.handleNamespaces(namespaces.message)
        this.addressSpaceSetup('namespaces')
      }).catch((err) => {
        ijtLog.error('namespacePromise failed:', err)
      })
    })
  }

  parseMaybeJson (value) {
    if (typeof value === 'string' || value instanceof String) {
      return JSON.parse(value.replace(/\n|\t/g, ''))
    }
    return value
  }

  /**
   * Sets up root and the Object folder and find a Tightening System
   */
  async initiate () {
    try {
      await this.findOrLoadNode('ns=0;i=84') // GRoot
      const objectFolder = await this.findOrLoadNode('ns=0;i=85')
      this.objectFolder = objectFolder
      const typerelations = objectFolder.getTypeDefinitionRelations('1005')
      if (!typerelations || typerelations.length === 0) {
        throw new Error('Could not find Tightening System')
      }
      const tgtSystem = await this.findOrLoadNode(typerelations[0].NodeId)
      this.tighteningSystem = tgtSystem
      this.addressSpaceSetup('tighteningsystem')
      this.connectionManager.trigger(this.connectionManager.CONNECTION_STATES.TIGHTENING_SYSTEM, true)
    } catch (err) {
      ijtLog.error('initiate failed:', err)
    }
  }

  /**
   * Check that addressSpace has been set up and a tightening system exists
   * @returns true if the addressSpace is set up
   */
  addressSpaceCheck () {
    return this.status.find(x => x === 'tighteningsystem')
    // return this.status.find(x => x === 'namespaces') && this.status.find(x => x === 'datatypes') && this.status.find(x => x === 'tighteningsystem')
  }

  /**
   * In setup, fullfill all previous promises
   * @param {*} status add this status
   */
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

  /**
   * return a promise to call a method
   * @param {*} locationId the parent node
   * @param {*} methodNode the method node
   * @param {*} args the arguments
   * @returns a promise of the json return value of the function
   */
  methodCall (locationId, methodNode, args) {
    return new Promise((resolve, reject) => {
      this.socketHandler.methodCall(locationId, methodNode, args).then(
        (result) => {
          resolve(this.parseMaybeJson(result.message.output))
        },
        (error) => {
          reject(error)
        }
      )
    })
  }

  /**
   * Supportfunction that determines the correct letter in a nodes address string
   * @param {} str the Identifier
   * @returns the right part of a nodestring
   */
  getIS (str) {
    if (Number(str)) {
      return ';i='
    }
    return ';s='
  }

  /**
   * Add a node to a list of cached nodes
   * @param {*} nodeId the nodes Id, can be a string or a nodeId object
   * @param {*} newNode the content of the node
   */
  setNodeMapping (nodeId, newNode) {
    if (typeof nodeId === 'string' || nodeId instanceof String) {
      this.nodeMapping[nodeId] = newNode
    } else {
      this.nodeMapping[`ns=${nodeId.NamespaceIndex}${this.getIS(nodeId.Identifier)}${nodeId.Identifier}`] = newNode
    }
  }

  /**
   * Return a cached node
   * @param {*} nodeId the nodes Id, can be a string or a nodeId object
   * @returns if the node has been cached, this will return the node object
   */
  getNodeMapping (nodeId) {
    if (typeof nodeId === 'string' || nodeId instanceof String) {
      return this.nodeMapping[nodeId]
    } else {
      return this.nodeMapping[`ns=${nodeId.NamespaceIndex}${this.getIS(nodeId.Identifier)}${nodeId.Identifier}`]
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
      return new Promise((resolve, reject) => {
        this.socketHandler.readPromise(nodeId, 'DisplayName, NodeClass').then(
          (response) => {
            const attributes = this.parseMaybeJson(response.message.attributes)
            const relations = this.parseMaybeJson(response.message.relations)
            const value = this.parseMaybeJson(response.message.value)
            const returnValue = {
              nodeid: response.message.nodeid,
              attributes,
              relations,
              value
            }
            resolve(returnValue)
          },
          (error) => {
            ijtLog.error(error)
            reject(error)
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
        }).catch(reject)
      })
    }
  }

  /**
   * This simplifies the use of the correct namespaces
   * @param {*} namespaces is the data sent bu the OPC UA client
   */
  handleNamespaces (namespaceMessage) {
    const namespaces = this.parseMaybeJson(namespaceMessage.namespaces)
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
            this.findOrLoadNode(this.parseMaybeJson(msg.message.nodeid)).then(
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
          }).catch(reject)
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
          ijtLog.error(error)
        })
    })
  }
}
