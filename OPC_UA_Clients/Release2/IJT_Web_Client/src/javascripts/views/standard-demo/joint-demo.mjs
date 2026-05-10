import BasicScreen from '../graphic-support/basic-screen.mjs' // Basic functionality application code for the screen functionality
import CommonPropertyView from './common-property-view.mjs' // The machine properties view
import { ijtLog } from '../../ijt-support/ijt-logger.mjs'

const SAMPLE_PRODUCT_INSTANCE_URIS = new Set([
  'www.company.com/ProductABC123',
  'www.atlascopco.com/CABLE-B0000000-',
])

/**
 * The purpose of this class is to generate an HTML representation of tightening selection and basic
 * display of a result for OPC UA Industrial Joining Technologies communication
 */
export default class JointDemo extends BasicScreen {
  constructor (methodManager, resultManager, connectionManager, settings) {
    super('Joint Demo') // Setting the name of the tab
    this.tabHelpText = 'Demo workflow for selecting tools and joints, then simulating tightening operations.'
    this.methodManager = methodManager
    this.resultManager = resultManager
    this.connectionManager = connectionManager
    this.settings = settings

    /** ProductInstanceUri explicitly selected from the tools table by the user. */
    this._selectedProductInstanceUri = null
    /** All tool rows fetched from the server: [{toolName, productInstanceUri, path}] */
    this._detectedTools = []
    /** Server-discovered joint IDs from GetJointList(ProductInstanceUri). */
    this._detectedJoints = []
    this._jointButtons = []

    // Create display areas
    const displayArea = document.createElement('div')
    this.backGround.appendChild(displayArea)
    this.backGround.classList.add('jointDemoScreen')
    this.container = displayArea

    this.activate()

    // When a new endpoint connects and methods load, refresh the tools table
    connectionManager.subscribe('methods', (setToTrue) => {
      if (setToTrue) {
        this._loadToolsFromServer()
      }
    })
  }

  /**
   * Run every time the tab is opened
   */
  initiate () {}

  /**
   * Priority resolution for ProductInstanceUri:
   *   1. Row explicitly selected by the user in the tools table
   *   2. Manual non-sample value from Settings
   *   3. First server-detected tool URI
   *   4. Sample Settings value as last-resort fallback
   */
  _getProductUri () {
    if (this._selectedProductInstanceUri) {
      return this._selectedProductInstanceUri
    }
    const manual = this._manualProductUri()
    if (manual && !this._isSampleProductUri(manual)) {
      return manual
    }
    return this._detectedProductUri() || manual || ''
  }

  _manualProductUri () {
    return String(this.settings?.productId || '').trim()
  }

  _detectedProductUri () {
    return String((this._detectedTools[0] && this._detectedTools[0].productInstanceUri) || '').trim()
  }

  _isSampleProductUri (uri) {
    const value = String(uri || '').trim()
    return !value || value === '-' || SAMPLE_PRODUCT_INSTANCE_URIS.has(value)
  }

  _callableProductUri () {
    const uri = this._getProductUri()
    if (!uri || this._isSampleProductUri(uri)) {
      ijtLog.warn(
        '[JointDemo] ProductInstanceUri is not resolved; skipping demo method call until a server tool or explicit Settings URI is available.'
      )
      this._updateActiveUriLabel()
      return ''
    }
    return uri
  }

  /**
   * Ask the backend to browse TighteningSystem/assets/Tools/ and return
   * all tool BrowseNames + ProductInstanceUri values.
   * Results populate the tools table; the active URI label is updated.
   */
  _loadToolsFromServer () {
    const socketHandler = this.methodManager?.addressSpace?.socketHandler
    if (!socketHandler) return

    socketHandler.readProductInstanceUri().then(({ message }) => {
      this._detectedTools = (message && message.tools) || []
      this._renderToolsTable()
      this._updateActiveUriLabel()
      return this._loadJointsFromServer()
    }).catch(err => {
      ijtLog.warn('[JointDemo] Could not read tool ProductInstanceUris:', err)
      this._renderToolsTable() // render empty / error state
      this._updateActiveUriLabel()
      this._updateJointButtons()
    })
  }

  async _loadJointsFromServer () {
    const getJointListMethod = this.methodManager?.getMethod('GetJointList')
    const productUri = this._getProductUri()
    if (!getJointListMethod || !productUri || this._isSampleProductUri(productUri)) {
      this._detectedJoints = []
      this._updateJointButtons()
      return
    }

    try {
      const output = await this.methodManager.call(getJointListMethod, [
        {
          value: productUri,
          type: getJointListMethod.arguments?.[0]?.DataType || { Identifier: '12' },
        },
      ])
      this._detectedJoints = this._extractJointIds(output)
    } catch (err) {
      ijtLog.warn('[JointDemo] Could not read server JointIds:', err)
      this._detectedJoints = []
    }
    this._updateJointButtons()
  }

  _extractJointIds (output) {
    const first = Array.isArray(output) && Array.isArray(output[0]) ? output[0] : output
    const entries = Array.isArray(first) ? first : [first]
    const ids = []
    for (const entry of entries) {
      const jointId = this._jointIdFromEntry(entry)
      if (jointId && !ids.includes(jointId)) ids.push(jointId)
    }
    return ids
  }

  _jointIdFromEntry (entry) {
    const value = entry?.Value ?? entry
    for (const source of [value, value?.JointMetaData]) {
      const jointId = source?.JointId ?? source?.Id
      if (jointId) return String(jointId).trim()
    }
    return typeof value === 'string' ? value.trim() : ''
  }

  _jointIdForButton (index) {
    const discovered = this._detectedJoints[index] || this._detectedJoints[0]
    const configured = index === 0 ? this.settings?.Joint1 : this.settings?.Joint2
    return String(discovered || configured || '').trim()
  }

  _updateJointButtons () {
    this._jointButtons.forEach((button, index) => {
      const jointId = this._jointIdForButton(index)
      const fallbackLabel = index === 0 ? 'primary joint' : 'secondary joint'
      button.innerText = jointId ? `Select ${jointId}` : `Select ${fallbackLabel}`
      button.title = jointId
        ? `Select server JointId: ${jointId}`
        : `Select ${fallbackLabel} after connecting to a server or configuring Settings.`
    })
  }

  /**
   * Render (or re-render) the tools table inside this._toolsTableContainer.
   */
  _renderToolsTable () {
    if (!this._toolsTableContainer) return
    this._toolsTableContainer.innerHTML = ''

    if (!this._detectedTools.length) {
      const msg = document.createElement('p')
      msg.textContent = 'No tools found on server (or not yet connected).'
      msg.classList.add('jointDemoHintText')
      this._toolsTableContainer.appendChild(msg)
      return
    }

    const table = document.createElement('table')
    table.classList.add('jointDemoToolsTable')

    // Header — built with DOM to avoid innerHTML with any variable content
    const thead = document.createElement('thead')
    const headerRow = document.createElement('tr')
    headerRow.classList.add('jointDemoToolsHeaderRow')
    const headerCells = [
      { text: 'Tool Name', align: 'left' },
      { text: 'ProductInstanceUri', align: 'left' },
      { text: 'Use', align: 'center' }
    ]
    for (const { text, align } of headerCells) {
      const th = document.createElement('th')
      th.textContent = text
      th.classList.add('jointDemoToolsHeaderCell')
      th.style.textAlign = align
      headerRow.appendChild(th)
    }
    thead.appendChild(headerRow)
    table.appendChild(thead)

    const tbody = document.createElement('tbody')
    this._detectedTools.forEach((tool, idx) => {
      const tr = document.createElement('tr')
      tr.classList.add('jointDemoToolsRow')
      tr.classList.add(idx % 2 === 0 ? 'jointDemoToolsRowEven' : 'jointDemoToolsRowOdd')

      const tdName = document.createElement('td')
      tdName.textContent = tool.toolName
      tdName.classList.add('jointDemoToolsCell', 'jointDemoToolsCellName')

      const tdUri = document.createElement('td')
      tdUri.textContent = tool.productInstanceUri
      tdUri.title = tool.productInstanceUri // full URI on hover
      tdUri.classList.add('jointDemoToolsCell', 'jointDemoToolsCellUri')

      const tdBtn = document.createElement('td')
      tdBtn.classList.add('jointDemoToolsCell', 'jointDemoToolsCellButton')
      const btn = document.createElement('button')
      btn.textContent = 'Use'
      btn.classList.add('jointDemoToolsUseButton')
      btn.addEventListener('click', () => {
        this._selectedProductInstanceUri = tool.productInstanceUri
        this._updateActiveUriLabel()
        this._loadJointsFromServer()
        // Highlight selected row
        tbody.querySelectorAll('tr').forEach(r => { r.classList.remove('jointDemoToolsRowSelected') })
        tr.classList.add('jointDemoToolsRowSelected')
      })
      tdBtn.appendChild(btn)

      tr.appendChild(tdName)
      tr.appendChild(tdUri)
      tr.appendChild(tdBtn)
      tbody.appendChild(tr)
    })
    table.appendChild(tbody)
    this._toolsTableContainer.appendChild(table)
  }

  /** Update the "Active URI" display line. */
  _updateActiveUriLabel () {
    if (!this._activeUriLabel) return
    const uri = this._getProductUri()
    const manual = this._manualProductUri()
    let source = '(sample setting fallback)'
    if (this._selectedProductInstanceUri) {
      source = '(selected from server)'
    } else if (manual && !this._isSampleProductUri(manual)) {
      source = '(from Settings)'
    } else if (this._detectedProductUri()) {
      source = '(auto-detected)'
    }
    this._activeUriLabel.textContent = `Active ProductInstanceUri: ${uri || '—'}  ${source}`
  }

  /**
  * Run activate when normal setup is done.
  * This queries the methodmanager for the available methods in the
  * given folders, and set up invokation buttons
  */
  activate () {
    this.container.classList.add('demoCol')

    const MESArea = document.createElement('div')
    MESArea.classList.add('demoRow', 'demoRelativeArea')

    const digTwinArea = this.makeNamedArea('Digital shadow', 'demoTwin', this.container)
    digTwinArea.appendChild(MESArea)

    // ── Joint selection buttons ───────────────────────────────────────────────
    const button1 = document.createElement('button')
    button1.innerText = 'Select primary joint'
    button1.classList.add('demoButtonFree', 'demoActionSelectJoint1')
    MESArea.appendChild(button1)
    button1.addEventListener('click', () => this.selectJoint(this._jointIdForButton(0)))

    const button2 = document.createElement('button')
    button2.innerText = 'Select secondary joint'
    button2.classList.add('demoButtonFree', 'demoActionSelectJoint2')
    MESArea.appendChild(button2)
    button2.addEventListener('click', () => this.selectJoint(this._jointIdForButton(1)))
    this._jointButtons = [button1, button2]
    this._updateJointButtons()

    const button3 = document.createElement('button')
    button3.innerText = 'Simulate tightening'
    button3.classList.add('demoButtonFree', 'demoActionSimulateTightening')
    MESArea.appendChild(button3)
    button3.addEventListener('click', () => this.simulateTightening())

    const img = document.createElement('img')
    img.src = '/src/resources/digital_twin.jpg'
    img.alt = 'A digital twin of a truck'
    img.height = 360
    img.width = 490
    MESArea.appendChild(img)

    // ── Tools table (ProductInstanceUri discovery) ────────────────────────────
    const toolsArea = this.makeNamedArea('Tools on Server', 'demoToolsArea', this.container)
    toolsArea.classList.add('jointDemoToolsArea')

    this._activeUriLabel = document.createElement('div')
    this._activeUriLabel.classList.add('jointDemoActiveUriLabel')
    this._activeUriLabel.textContent = 'Active ProductInstanceUri: — (not yet loaded)'
    toolsArea.appendChild(this._activeUriLabel)

    this._toolsTableContainer = document.createElement('div')
    toolsArea.appendChild(this._toolsTableContainer)

    // Placeholder while not connected
    const placeholder = document.createElement('p')
    placeholder.textContent = 'Connect to a server to discover tools and their ProductInstanceUri.'
    placeholder.classList.add('jointDemoHintText')
    this._toolsTableContainer.appendChild(placeholder)

    // ── Result area ───────────────────────────────────────────────────────────
    const resultArea = document.createElement('div')
    resultArea.classList.add('demoCol', 'demoMainArea')
    this.container.appendChild(resultArea)

    const resultTopArea = document.createElement('div')
    resultTopArea.classList.add('demoRow', 'demoTopPane')
    resultArea.appendChild(resultTopArea)

    const infoArea = this.makeNamedArea('Common Result Data', 'demoMachine', resultTopArea)

    this.propertyView = new CommonPropertyView(
      ['result.ResultMetaData.Name',
        'result.ResultMetaData.ResultEvaluation',
        'result.ResultMetaData.CreationTime',
        'result.ResultMetaData.SequenceNumber',
        'result.ResultMetaData.ResultId',
        'result.ResultMetaData.ProgramId'],
      infoArea,
      this.resultManager)

    const resultBottomArea = document.createElement('div')
    resultBottomArea.classList.add('demoBottomPane')
    resultArea.appendChild(resultBottomArea)

    const backGround = document.createElement('div')
    backGround.classList.add('myInfoArea')
    resultBottomArea.appendChild(backGround)
  }

  /**
   * Call StartSelectedJoining.
   * ProductInstanceUri must resolve to a selected row, manual non-sample Settings
   * value, or server-detected tool URI before the call is sent.
   */
  simulateTightening () {
    const selectJoiningProcessMethod = this.methodManager.getMethod('StartSelectedJoining')
    if (!selectJoiningProcessMethod) {
      return
    }
    const productUri = this._callableProductUri()
    if (!productUri) {
      return
    }

    const values = [
      {
        value: productUri,
        type: {
          pythonclass: 'NodeId',
          Identifier: '12',
          NamespaceIndex: '0',
          NodeIdType: 'NodeIdType.TwoByte',
        },
      },
      {
        type: {
          Identifier: '1',
        },
        value: false,
      },
    ]

    this.methodManager.call(selectJoiningProcessMethod, values).then(
      (_success) => {},
      (fail) => { ijtLog.error(JSON.stringify(fail)) }
    )
  }

  /**
   * Call SelectJoint.
   * ProductInstanceUri must resolve to a selected row, manual non-sample Settings
   * value, or server-detected tool URI before the call is sent.
   * @param {string} jointName  The server-discovered or user-configured JointId to select.
   */
  selectJoint (jointName) {
    const selectJointMethod = this.methodManager.getMethod('SelectJoint')
    if (!selectJointMethod) {
      return
    }
    const productUri = this._callableProductUri()
    if (!productUri) {
      return
    }
    const jointId = String(jointName || '').trim()
    if (!jointId || jointId === '-') {
      ijtLog.warn('[JointDemo] JointId is not resolved; skipping SelectJoint until server joints or Settings are available.')
      return
    }

    const values = [
      {
        value: productUri,
        type: {
          pythonclass: 'NodeId',
          Identifier: '12',
          NamespaceIndex: '0',
          NodeIdType: 'NodeIdType.TwoByte',
        },
      },
      {
        type: {
          Identifier: '31918',
        },
        value: jointId,
      },
      {
        type: {
          Identifier: '31918',
        },
        value: '',
      },
    ]

    this.methodManager.call(selectJointMethod, values).then(
      (_success) => {},
      (fail) => { ijtLog.error(JSON.stringify(fail)) }
    )
  }
}
