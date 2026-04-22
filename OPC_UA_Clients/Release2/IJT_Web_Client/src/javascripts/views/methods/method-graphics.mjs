import ControlMessageSplitScreen from '../graphic-support/control-message-split-screen.mjs'
import MethodGUICreator from './method-gui-creator.mjs'
import { ijtLog } from '../../ijt-support/ijt-logger.mjs'
/**
 * The purpose of this class is to generate an HTML representation of method
 * invocations for OPC UA Industrial Joining Technologies
 */
export default class MethodGraphics extends ControlMessageSplitScreen {
  constructor (methodManager, addressSpace, settings, entityManager) {
    super('Methods', 'Calls', 'Results')
    this.tabHelpText = 'Invoke available OPC UA methods and inspect call responses for this endpoint.'
    this.backGround.classList.add('methodsScreen')
    this.methodManager = methodManager
    this.settings = settings
    this.entityManager = entityManager
    this.methodGUICreator = new MethodGUICreator(this, methodManager, entityManager, settings)
    this.ensureStatusBanner('methods')
    this.setStatusBanner('methods', 'info', 'Waiting for endpoint connection.')

    this.addressSpace = addressSpace // This is just used to get the namespace number. Can this be done in a better way?
    addressSpace.connectionManager.subscribe('tighteningsystem', (setToTrue) => {
      if (setToTrue) {
        try {
          this.setStatusBanner('methods', 'loading', 'Loading methods...')
          this.activate()
        } catch (error) {
          this.setStatusBanner('methods', 'error', `Failed to load methods: ${error?.message || error}`)
          ijtLog.error('Error in activating method view')
          ijtLog.error(`${error.name}: ${error.message}`)
        }
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
      return this.settings.settingPromise().then(() => {
        const methodNames = this.methodManager.getMethodNames()
        this.createMethodAreas(methodNames)
        if (methodNames.length === 0) {
          this.setStatusBanner('methods', 'empty', 'No methods available for this endpoint.')
        } else {
          this.setStatusBanner('methods', 'success', `${methodNames.length} methods ready.`)
        }
      })
    }).catch((error) => {
      this.setStatusBanner('methods', 'error', `Method discovery failed: ${error?.message || error}`)
      ijtLog.error('Method discovery failed')
      ijtLog.error(error)
    })
  }

  /**
   * Given a list of method names, create invokation areas for them
   * @param {*} methodNames a list of method names
   */
  createMethodAreas (methodNames) {
    for (const name of methodNames) {
      const methodArea = this.methodGUICreator.createMethodArea(name)
      this.controls.appendChild(methodArea)
    }
  }
}
