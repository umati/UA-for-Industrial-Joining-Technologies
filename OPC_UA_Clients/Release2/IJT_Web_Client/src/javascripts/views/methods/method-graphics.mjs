import ControlMessageSplitScreen from '../graphic-support/control-message-split-screen.mjs'
import MethodGUICreator from './method-gui-creator.mjs'
import { ijtLog } from '../../ijt-support/ijt-logger.mjs'
import { firstProductInstanceUri } from '../../ijt-support/tools/product-instance-uri.mjs'
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
      [{ namespaceindex: this.addressSpace.nsTighteningServer, identifier: 'Simulations' }],
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
        return this.resolveMethodProductInstanceUri()
      }).then(() => {
        this.controls.innerHTML = ''
        this.methodManager.setMethodMetadata(this.settings.methodMetadata || {})
        const methodNames = this.methodManager.getMethodNames()
        this.createMethodAreas()
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

  async resolveMethodProductInstanceUri () {
    const socketHandler = this.addressSpace?.socketHandler
    if (typeof socketHandler?.readProductInstanceUri !== 'function') {
      return
    }
    try {
      const response = await socketHandler.readProductInstanceUri()
      const productInstanceUri = firstProductInstanceUri(response)
      if (productInstanceUri) {
        this.settings.methodProductInstanceUri = productInstanceUri
      }
    } catch (error) {
      ijtLog.warn('Could not resolve Tool.ProductInstanceUri for method defaults:', error)
    }
  }

  /**
   * Given a list of method names, create invokation areas for them
   * @param {*} methodNames a list of method names
   */
  createMethodAreas () {
    const groupedMethods = this.methodManager.getGroupedMethods()
    const filterArea = document.createElement('div')
    filterArea.classList.add('methodFilter')
    const filterLabel = this.createLabel('Find a method')
    filterLabel.classList.add('methodFilterLabel')
    filterLabel.htmlFor = 'method-filter-input'
    const filterInput = document.createElement('input')
    filterInput.id = 'method-filter-input'
    filterInput.type = 'search'
    filterInput.classList.add('methodInput')
    filterInput.placeholder = 'Search by method, domain, or argument'
    filterInput.setAttribute('aria-label', 'Find a method')
    filterArea.append(filterLabel, filterInput)
    this.controls.appendChild(filterArea)

    const filterMethods = () => {
      const query = filterInput.value.trim().toLowerCase()
      for (const groupArea of this.controls.querySelectorAll('.methodGroup:not(.methodDomainGroup)')) {
        let groupVisible = false
        for (const methodArea of groupArea.querySelectorAll('.methodBorder')) {
          const searchable = methodArea.dataset.methodSearch || ''
          const visible = !query || searchable.includes(query)
          methodArea.hidden = !visible
          groupVisible ||= visible
        }
        groupArea.hidden = !groupVisible
        if (query && groupVisible) groupArea.open = true
      }
      for (const domainArea of this.controls.querySelectorAll('.methodDomainGroup')) {
        const domainVisible = [...domainArea.querySelectorAll('.methodGroup:not(.methodDomainGroup)')]
          .some(groupArea => !groupArea.hidden)
        domainArea.hidden = !domainVisible
        if (query && domainVisible) domainArea.open = true
      }
    }
    filterInput.addEventListener('input', filterMethods)

    const domainAreas = new Map()
    for (const group of groupedMethods) {
      let groupParent = this.controls
      if (group.parentId) {
        let domainArea = domainAreas.get(group.parentId)
        if (!domainArea) {
          domainArea = document.createElement('details')
          domainArea.classList.add('methodGroup', 'methodDomainGroup')
          domainArea.dataset.methodDomain = group.parentId
          domainArea.open = group.parentId === 'simulations'

          const domainSummary = document.createElement('summary')
          domainSummary.classList.add('methodGroupSummary')
          const domainLabel = document.createElement('span')
          domainLabel.classList.add('methodGroupTitle')
          domainLabel.textContent = group.parentLabel
          domainSummary.appendChild(domainLabel)
          domainArea.appendChild(domainSummary)

          const domainContent = document.createElement('div')
          domainContent.classList.add('methodGroupContent', 'methodDomainGroupContent')
          if (group.parentDescription) {
            const description = document.createElement('p')
            description.classList.add('methodGroupDescription')
            description.textContent = group.parentDescription
            domainContent.appendChild(description)
          }
          domainArea.appendChild(domainContent)
          this.controls.appendChild(domainArea)
          domainAreas.set(group.parentId, domainArea)
        }
        groupParent = domainArea.querySelector('.methodDomainGroupContent')
      }

      const groupArea = document.createElement('details')
      groupArea.classList.add('methodGroup')
      groupArea.dataset.methodGroup = group.id
      groupArea.open = group.id === 'simulate-results'

      const groupSummary = document.createElement('summary')
      groupSummary.classList.add('methodGroupSummary')
      const titleLabel = document.createElement('span')
      titleLabel.classList.add('methodGroupTitle')
      titleLabel.textContent = group.label
      groupSummary.appendChild(titleLabel)

      const methodCount = document.createElement('span')
      methodCount.classList.add('methodGroupCount')
      methodCount.textContent = `${group.methods.length} methods`
      groupSummary.appendChild(methodCount)
      groupArea.appendChild(groupSummary)

      const groupContent = document.createElement('div')
      groupContent.classList.add('methodGroupContent')

      if (group.description) {
        const desc = document.createElement('p')
        desc.classList.add('methodGroupDescription')
        desc.textContent = group.description
        groupContent.appendChild(desc)
      }

      for (const method of group.methods) {
        const methodArea = this.methodGUICreator.createMethodArea(method.name)
        const argumentNames = method.methodData.arguments.map(arg => arg?.Name || '').join(' ')
        methodArea.dataset.methodSearch = `${group.parentLabel} ${group.label} ${group.description} ${method.name} ${argumentNames}`.toLowerCase()
        groupContent.appendChild(methodArea)
      }
      groupArea.appendChild(groupContent)
      groupParent.appendChild(groupArea)
    }
  }
}
