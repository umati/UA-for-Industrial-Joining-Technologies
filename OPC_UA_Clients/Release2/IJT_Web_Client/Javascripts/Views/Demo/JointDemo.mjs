import BasicScreen from '../GraphicSupport/BasicScreen.mjs' // Basic functionality application code for the screen functionality
import CommonPropertyView from './CommonPropertyView.mjs' // The machine properties view
import IJTPropertyView from './IJTPropertyView.mjs' // The machine properties view

/**
 * The purpose of this class is to generate an HTML representation of tightening selection and basic
 * display of a result for OPC UA Industrial Joining Technologies communication
 */
export default class JointDemo extends BasicScreen {
  constructor (methodManager, resultManager, connectionManager, settings) {
    super('JointDemo', 'tighteningsystem') // Setting the name of the tab
    this.methodManager = methodManager
    this.resultManager = resultManager
    this.settings = settings

    // Create display areas
    const displayArea = document.createElement('div')
    this.backGround.appendChild(displayArea)
    this.container = displayArea
    
    this.activate()

    // Wait until the methods have loaded
    connectionManager.subscribe('methods', (setToTrue) => {
      if (setToTrue) {
   //     this.activate()
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
  * given folders, and set up invokation buttons
  */
  activate () {
    this.container.classList.add('demoCol')

    const MESArea = document.createElement('div')
    MESArea.classList.add('demoRow')
    //this.container.appendChild(MESArea)
    MESArea.style.position = 'relative'

    const digTwinArea = this.makeNamedArea('Digital twin', 'demoTwin',  this.container)

    digTwinArea.appendChild(MESArea)

    // Handling of button 1 (calling select joint 1)
    const button1 = document.createElement('button')
    button1.innerText = 'Select joint 1'
    button1.classList.add('demoButtonFree')
    button1.style.left = '35px'
    button1.style.top = '45px'
    button1.title = 
    `Joint data
    Joint Id: joint_1
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

    // Handling of button 2 (calling select joint 2)
    const button2 = document.createElement('button')
    button2.innerText = 'Select joint 2'
    button2.classList.add('demoButtonFree')
    button2.style.left = '420px'
    button2.style.top = '65px'
    
    button2.title = 
    `Joint data
    Joint Id: joint_2
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

    // Handling of button 2 (calling select joint 2)
    const button3 = document.createElement('button')
    button3.innerText = 'Simulate tightening'
    button3.classList.add('demoButtonFree')
    button3.style.right = '10px'
    button3.style.top = '300px'
    MESArea.appendChild(button3)
    button3.addEventListener('click', () => this.simulateTightening())

    const img = document.createElement('img')

    // Set the image source and attributes
    img.src = './Resources/digital_twin.jpg'
    img.alt = 'A digital twin of a truck'
    img.height = 360 // Set height (optional)
    img.width = 490 // Set width (optional)

    MESArea.appendChild(img)

    const resultArea = document.createElement('div')
    resultArea.style.width = '80%'
    resultArea.classList.add('demoCol')
    this.container.appendChild(resultArea)

    const resultTopArea = document.createElement('div')
    resultTopArea.style.height = '200px'
    resultTopArea.classList.add('demoRow')
    resultArea.appendChild(resultTopArea)

    // Set up the common parts of the result
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

    // Set up the specific tightening related parameters of the reult
    //const tqAngleBox = this.makeNamedArea('Tightening Result Data', 'demoMachine', resultTopArea)
    //this.IJTpropertyView = new IJTPropertyView(tqAngleBox, this.resultManager)

    const resultBottomArea = document.createElement('div')
    resultBottomArea.style.height = '50%'
    resultBottomArea.style.margin = '5px'
    resultArea.appendChild(resultBottomArea)

    const backGround = document.createElement('div')
    backGround.classList.add('myInfoArea')
    resultBottomArea.appendChild(backGround)
  }

  /**
   * This function selects a tightening process on the tool
   * @param {*} process The identity of the tightening program
   * @returns Nothing
   */
  simulateTightening () {
    const selectJoiningProcessMethod = this.methodManager.getMethod('StartSelectedJoining')
    if (!selectJoiningProcessMethod) {
      return
    }

    const values = [
      {
        value: this.settings.productId,
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
      (success) => {
        // console.log(JSON.stringify(success))
      },
      (fail) => {
        console.log(JSON.stringify(fail))
      }
    )
  }

  /**
   * This function selects a tightening process on the tool
   * @param {*} process The identity of the tightening program
   * @returns Nothing
   */
  selectJoint (jointName) {
    const selectJointMethod = this.methodManager.getMethod('SelectJoint')
    if (!selectJointMethod) {
      return
    }

    const values = [
      {
        value: this.settings.productId,
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
      (success) => {
        // console.log(JSON.stringify(success))
      },
      (fail) => {
        console.log(JSON.stringify(fail))
      }
    )
  }
}
