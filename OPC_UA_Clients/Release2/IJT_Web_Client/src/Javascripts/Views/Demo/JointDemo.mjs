import BasicScreen from '../GraphicSupport/BasicScreen.mjs' // Basic functionality application code for the screen functionality
import CommonPropertyView from './CommonPropertyView.mjs' // The machine properties view

/**
 * The purpose of this class is to generate an HTML representation of tightening selection and basic
 * display of a result for OPC UA Industrial Joining Technologies communication
 */
export default class JointDemo extends BasicScreen {
  constructor (methodManager, resultManager, connectionManager, settings) {
    super('JointDemo') // Setting the name of the tab
    this.methodManager = methodManager
    this.resultManager = resultManager
    this.connectionManager = connectionManager
    this.settings = settings

    /** ProductInstanceUri explicitly selected from the tools table by the user. */
    this._selectedProductInstanceUri = null
    /** All tool rows fetched from the server: [{toolName, productInstanceUri, path}] */
    this._detectedTools = []

    // Create display areas
    const displayArea = document.createElement('div')
    this.backGround.appendChild(displayArea)
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
   *   2. Manual value from Settings (if not the placeholder '-')
   *   3. First auto-detected tool URI (fallback)
   */
  _getProductUri () {
    if (this._selectedProductInstanceUri) {
      return this._selectedProductInstanceUri
    }
    const manual = this.settings.productId
    if (manual && manual !== '-') {
      return manual
    }
    return (this._detectedTools[0] && this._detectedTools[0].productInstanceUri) || manual || ''
  }

  /**
   * Ask the backend to browse TighteningSystem/Assets/Tools/ and return
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
    }).catch(err => {
      console.warn('[JointDemo] Could not read tool ProductInstanceUris:', err)
      this._renderToolsTable() // render empty / error state
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
      msg.style.cssText = 'color:#888;font-style:italic;margin:4px 0;'
      this._toolsTableContainer.appendChild(msg)
      return
    }

    const table = document.createElement('table')
    table.style.cssText = 'width:100%;border-collapse:collapse;font-size:0.85em;'

    // Header
    const thead = document.createElement('thead')
    thead.innerHTML = `
      <tr style="background:#2a2a2a;color:#ccc;">
        <th style="padding:4px 8px;text-align:left;border-bottom:1px solid #444;">Tool Name</th>
        <th style="padding:4px 8px;text-align:left;border-bottom:1px solid #444;">ProductInstanceUri</th>
        <th style="padding:4px 8px;text-align:center;border-bottom:1px solid #444;">Use</th>
      </tr>`
    table.appendChild(thead)

    const tbody = document.createElement('tbody')
    this._detectedTools.forEach((tool, idx) => {
      const tr = document.createElement('tr')
      tr.style.cssText = idx % 2 === 0 ? 'background:#1e1e1e;' : 'background:#252525;'

      const tdName = document.createElement('td')
      tdName.textContent = tool.toolName
      tdName.style.cssText = 'padding:4px 8px;color:#ddd;'

      const tdUri = document.createElement('td')
      tdUri.textContent = tool.productInstanceUri
      tdUri.title = tool.productInstanceUri // full URI on hover
      tdUri.style.cssText = 'padding:4px 8px;color:#adf;max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'

      const tdBtn = document.createElement('td')
      tdBtn.style.cssText = 'padding:2px 8px;text-align:center;'
      const btn = document.createElement('button')
      btn.textContent = 'Use'
      btn.style.cssText = 'font-size:0.8em;padding:2px 8px;cursor:pointer;'
      btn.addEventListener('click', () => {
        this._selectedProductInstanceUri = tool.productInstanceUri
        this._updateActiveUriLabel()
        // Highlight selected row
        tbody.querySelectorAll('tr').forEach(r => { r.style.outline = '' })
        tr.style.outline = '2px solid #5af'
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
    const source = this._selectedProductInstanceUri
      ? '(selected from server)'
      : (this.settings.productId && this.settings.productId !== '-')
          ? '(from Settings)'
          : '(auto-detected)'
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
    button1.innerText = 'Select joint 1'
    button1.classList.add('demoButtonFree', 'demoActionSelectJoint1')
    button1.title =
    `Joint data
    Joint Id: Joint_1
    Joint name: Engine front top joint
    Joint material:
      0.015 Steel
      0.010 Steel
    Joint location: {x: 0.1, y: 0.15, z:0.22}
    Joint context: Engine
    Bolt type: M8
    Bolt tread length: 0.05
    Bolt geometry: Hex
    Bolt Material: 304 Stainless steel
    Bolt grade: 4.8 / A2-70
     
    Associated program name: Program_4_Steps
    Associated program identity: 153X-FFTS-LJ67-99MM
    `
    MESArea.appendChild(button1)
    button1.addEventListener('click', () => this.selectJoint(this.settings.Joint1))

    const button2 = document.createElement('button')
    button2.innerText = 'Select joint 2'
    button2.classList.add('demoButtonFree', 'demoActionSelectJoint2')
    button2.title =
    `Joint data
    Joint Id: Joint_2
    Joint name: Engine back nut joint
    Joint material:
      0.010 Steel
      0.030 Steel
    Joint location: {x: 1.1, y: 0.55, z:0.22}
    Joint context: Engine
    Bolt type: M8
    Bolt tread length: 0.06
    Nut geometry: Hex
    Bolt Material: 304 Stainless steel
    Bolt grade: 4.8 / A2-70
     
    Associated program name: Program_One_Step
    Associated program identity: 66JA-UUOJ-FFTS-8MMM
    `
    MESArea.appendChild(button2)
    button2.addEventListener('click', () => this.selectJoint(this.settings.Joint2))

    const button3 = document.createElement('button')
    button3.innerText = 'Simulate tightening'
    button3.classList.add('demoButtonFree', 'demoActionSimulateTightening')
    MESArea.appendChild(button3)
    button3.addEventListener('click', () => this.simulateTightening())

    const img = document.createElement('img')
    img.src = '/src/Resources/digital_twin.jpg'
    img.alt = 'A digital twin of a truck'
    img.height = 360
    img.width = 490
    MESArea.appendChild(img)

    // ── Tools table (ProductInstanceUri discovery) ────────────────────────────
    const toolsArea = this.makeNamedArea('Tools on Server', 'demoToolsArea', this.container)
    toolsArea.style.cssText = 'margin:8px 0;padding:6px;'

    this._activeUriLabel = document.createElement('div')
    this._activeUriLabel.style.cssText = 'font-size:0.8em;color:#aaa;margin-bottom:6px;'
    this._activeUriLabel.textContent = 'Active ProductInstanceUri: — (not yet loaded)'
    toolsArea.appendChild(this._activeUriLabel)

    this._toolsTableContainer = document.createElement('div')
    toolsArea.appendChild(this._toolsTableContainer)

    // Placeholder while not connected
    const placeholder = document.createElement('p')
    placeholder.textContent = 'Connect to a server to discover tools and their ProductInstanceUri.'
    placeholder.style.cssText = 'color:#888;font-style:italic;margin:4px 0;font-size:0.85em;'
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
   * ProductInstanceUri priority: selected-from-table → Settings → auto-detected first tool.
   */
  simulateTightening () {
    const selectJoiningProcessMethod = this.methodManager.getMethod('StartSelectedJoining')
    if (!selectJoiningProcessMethod) {
      return
    }

    const values = [
      {
        value: this._getProductUri(),
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
      (fail) => { console.log(JSON.stringify(fail)) }
    )
  }

  /**
   * Call SelectJoint.
   * ProductInstanceUri priority: selected-from-table → Settings → auto-detected first tool.
   * @param {string} jointName  The JointId to select (e.g. 'Joint_1').
   */
  selectJoint (jointName) {
    const selectJointMethod = this.methodManager.getMethod('SelectJoint')
    if (!selectJointMethod) {
      return
    }

    const values = [
      {
        value: this._getProductUri(),
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
        value: jointName,
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
      (fail) => { console.log(JSON.stringify(fail)) }
    )
  }
}
