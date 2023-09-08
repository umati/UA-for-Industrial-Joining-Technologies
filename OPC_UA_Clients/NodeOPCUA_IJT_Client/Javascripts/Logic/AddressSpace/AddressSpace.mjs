import { NodeFactory } from './Node.mjs'

export default class AddressSpace {
  constructor (socketHandler) {
    this.socketHandler = socketHandler
    this.nodeMapping = {}
    this.objectFolder = null
    this.listOfTSPromises = []
    this.ParentRelationSubscription = []
    this.newNodeSubscription = []
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
      let newNode = this.nodeMapping[nodeData.nodeid]

      if (!newNode) {
        newNode = NodeFactory(nodeData)
        this.nodeMapping[newNode.nodeId] = newNode
      }

      for (const callback of this.newNodeSubscription) {
        callback(newNode)
      }
      return newNode
    }

    /**
     * This function is a promise to load the relevant data and then resolv a special structure that
     * can be set up to create a node. Most often loadAndCreate works better
     * @param {*} nodeId the node identity
     * @param {*} details do we want the extra data from the browse?
     * @returns a promise of a datastructure that can be used to create a node
     */
    const browseAndRead = (nodeId, details = false) => {
      return this.socketHandler.browsePromise(nodeId, details).then(
        (browseMsg) => {
          return new Promise((resolve) => {
            this.socketHandler.readPromise(nodeId, 'DisplayName').then(
              (readname) => {
                return new Promise(() => {
                  this.socketHandler.readPromise(nodeId, 'NodeClass').then(
                    (readclass) => {
                      const returnValue = {
                        nodeid: browseMsg.message.nodeid,
                        nodeclass: readclass.message.dataValue.value,
                        displayname: readname.message.dataValue.value,
                        relations: browseMsg.message.browseresult.references
                      }
                      if (readclass.message.dataValue.value.value === 2) {
                        return new Promise(() => {
                          this.socketHandler.readPromise(nodeId, 'Value').then(
                            (value) => {
                              returnValue.value = value
                              resolve(returnValue)
                            })
                        })
                      } else {
                        resolve(returnValue)
                      }
                    })
                })
              })
          })
        })
    }

    const returnNode = this.nodeMapping[nodeId]
    if (returnNode) {
      return new Promise((resolve, reject) => {
        resolve(returnNode, false)
      })
    } else {
      return new Promise((resolve, reject) => {
        browseAndRead(nodeId, true).then((m) => {
          resolve(createNode(m), true)
        })
      })
    }
  }

  handleNamespaces (namespaces) {
    this.OPCUA = namespaces.indexOf('http://opcfoundation.org/UA/')
    this.nsIJT = namespaces.indexOf('http://opcfoundation.org/UA/IJT/')
    this.nsMachinery = namespaces.indexOf('http://opcfoundation.org/UA/Machinery/')
    this.nsDI = namespaces.indexOf('http://opcfoundation.org/UA/DI/')
    this.nsIJTApplication = namespaces.indexOf('http://www.atlascopco.com/TighteningApplication/')
  }

  /**
   * Sets up root and the Object folder and find a Tightening System
   */
  initiate () {
    this.findOrLoadNode('ns=0;i=84').then((rootFolder) => { // GRoot
      this.findOrLoadNode('ns=0;i=85').then((objectFolder) => {
        this.objectFolder = objectFolder
        const typerelations = objectFolder.getTypeDefinitionRelations('ns=4;i=1005')
        if (!typerelations || typerelations.length === 0) {
          throw new Error('Could not find Tightening System')
        }
        this.findOrLoadNode(typerelations[0].nodeId).then((tgtSystem) => {
          for (const promise of this.listOfTSPromises) {
            this.tighteningSystem = tgtSystem
            promise.resolve(tgtSystem)
          }
        })
      })
    })
  }

  reset () {
    this.nodeMapping = {}
  }

  getTighteningsSystemsPromise () {
    return new Promise((resolve, reject) => {
      if (this.tighteningSystem) {
        resolve(this.tighteningSystem)
        return
      }
      this.listOfTSPromises.push({ resolve, reject })
    }
    )
  }

  /**
   * note that this normally only returns the call message, not the actual node as might be expected.
   * The nodeId needs to be extracted from the message.
   * @param {*} path The path that should be traversed
   * @param {*} startFolderId The starting node
   * @returns the call message
   */
  findFolder (path, startFolderId) {
    if (!startFolderId) {
      const tgtSystem = this.getTighteningSystems()
      if (tgtSystem.length > 0) {
        startFolderId = tgtSystem[0].nodeId
      } else {
        throw new Error('Failed to find starting folder')
      }
    }
    return this.socketHandler.pathtoidPromise(startFolderId, path)
  }

  subscribeToNewNode (callback) {
    this.newNodeSubscription.push(callback)
  }

  subscribeToParentRelation (callback) {
    this.ParentRelationSubscription.push(callback)
  }

  /**
   * This function is a promise to load the relevant data and then resolv a special structure that
   * can be set up to create a node. Most often loadAndCreate works better
   * @param {*} nodeId the node identity
   * @param {*} details do we want the extra data from the browse?
   * @returns a promise of a datastructure that can be used to create a node
  browseAndRead (nodeId, details = false) {
    return this.socketHandler.browsePromise(nodeId, details).then(
      (browseMsg) => {
        return new Promise((resolve) => {
          this.socketHandler.readPromise(nodeId, 'DisplayName').then(
            (readname) => {
              return new Promise(() => {
                this.socketHandler.readPromise(nodeId, 'NodeClass').then(
                  (readclass) => {
                    const returnValue = {
                      nodeid: browseMsg.message.nodeid,
                      nodeclass: readclass.message.dataValue.value,
                      displayname: readname.message.dataValue.value,
                      relations: browseMsg.message.browseresult.references
                    }
                    if (readclass.message.dataValue.value.value === 2) {
                      return new Promise(() => {
                        this.socketHandler.readPromise(nodeId, 'Value').then(
                          (value) => {
                            returnValue.value = value
                            resolve(returnValue)
                          })
                      })
                    } else {
                      resolve(returnValue)
                    }
                  })
              })
            })
        })
      })
  } */

  /**
   * Supportfunction that takes the data from browseAndRead and turn it into an actual node
   * @param {*} nodeData the data from browseAndRead
   * @returns a node

  createNode (nodeData) {
    let newNode = this.nodeMapping[nodeData.nodeid]

    if (!newNode) {
      newNode = NodeFactory(nodeData)
      this.nodeMapping[newNode.nodeId] = newNode
    }

    for (const callback of this.newNodeSubscription) {
      callback(newNode)
    }
    return newNode
  } */

  /**
   * Turn a list of relations into a promise of a list of node
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
          this.findOrLoadNode(relation.nodeId).then((node) => {
            resolve(node)
          })
        })
      )
    }

    return Promise.all(promiseList)
  }

  read (nodeId, attribute) {
    // console.log('SEND Read: '+this.nodeId)
    return new Promise((resolve) => {
      this.socketHandler.readPromise(nodeId, attribute).then(
        (response) => {
          resolve(response.node)
        })
    })
  }
}
