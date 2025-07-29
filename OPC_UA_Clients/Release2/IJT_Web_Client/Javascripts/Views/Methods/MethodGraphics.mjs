import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'
import MethodGUICreator from './MethodGUICreator.mjs'
/**
 * The purpose of this class is to generate an HTML representation of method
 * invocations for OPC UA Industrial Joining Technologies
 */
export default class MethodGraphics extends ControlMessageSplitScreen {
  constructor (methodManager, addressSpace, settings, entityManager) {
    super('Methods', 'Methods', 'Call results')
    this.methodManager = methodManager
    this.settings = settings
    this.entityManager = entityManager
    this.methodGUICreator = new MethodGUICreator(this, methodManager, entityManager, settings)

    this.addressSpace = addressSpace // This is just used to get the namespace number. Can this be done in a better way?
    addressSpace.connectionManager.subscribe('tighteningsystem', (setToTrue) => {
      if (setToTrue) {
        this.activate()
      }
    })
  }

  /**
   * Run everytime the tab is opened
   */
  initiate () {
  }

  /**
  * Run activate when normal setup is done.
  * This queries the methodmanager for the available methods in the
  * given folders, and set up invokation buttons for all found methods
  */
  activate () {
    const methodFolders = [ // These folders should be searched for methods
      [{ namespaceindex: this.addressSpace.nsTighteningServer, identifier: 'Simulations' },
        { namespaceindex: this.addressSpace.nsTighteningServer, identifier: 'SimulateResults' }],
      [{ namespaceindex: this.addressSpace.nsIJT, identifier: 'AssetManagement' },
        { namespaceindex: this.addressSpace.nsIJT, identifier: 'MethodSet' }],
      [{ namespaceindex: this.addressSpace.nsIJT, identifier: 'JoiningProcessManagement' }],
      [{ namespaceindex: this.addressSpace.nsIJT, identifier: 'JointManagement' }],
      [{ namespaceindex: this.addressSpace.nsMachineryResult, identifier: 'ResultManagement' }],
      [{ namespaceindex: this.addressSpace.nsTighteningServer, identifier: 'Simulations' },
        { namespaceindex: this.addressSpace.nsTighteningServer, identifier: 'SimulateEventsAndConditions' }],
    ]

    this.methodManager.setupMethodsInFolders(methodFolders).then(() => {
      this.settings.settingPromise().then(() => {
        this.createMethodAreas(this.methodManager.getMethodNames())
      })
    })
  }

  /**
   * Given a list of method names, create invokation areas for them
   * @param {*} methodNames a list of method names
   */
  createMethodAreas (methodNames) {
    for (const name of methodNames) {
      const methodArea = this.methodGUICreator.createMethodArea(name)
      this.controlArea.appendChild(methodArea)
    }
  }
}
