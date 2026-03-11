import { JointDataType } from '../../ijt-support/Models/Joints/JointDataType.mjs'
import ControlSplitScreen from '../GraphicSupport/ControlSplitScreen.mjs'
import MethodGUICreator from '../Methods/MethodGUICreator.mjs'

export default class JointGraphics extends ControlSplitScreen {
  constructor (jointManager) {
    super('Joints', 'Joints', 'Joint Data')
    this.jointManager = jointManager
    this.methodGUICreator = new MethodGUICreator(this, null, jointManager, null)

    // this.setupSomeEntities()

    jointManager.subscribe((allJoints, justAddedEntity) => {
      this.displayJoints()
    })

    this.displayJoints()
  }

  /**
   * Display a specific Entity for editing
   * @param {*} joint The joint that should be edited
   * @param {*} view The background view object inheriting the BaseScreen functionality
   */
  displayJoints (joint, view) {
    const identifier = document.createElement('div')
    view.views.innerHTML = ''
    view.views.appendChild(identifier)

    const displayList = [
      { name: 'EntityType', type: 'DropDown' },
      { name: 'JointId', type: '12' },
      { name: 'Name', type: '12' },
      { name: 'EntityOriginId', type: '12' },
      { name: 'IsExternal', type: '1' },
      { name: 'Description', type: '12' }
    ]

    for (const display of displayList) {
      const arg = {
        Name: display.name,
        DataType: {
          Identifier: display.type
        }
      }

      const area = document.createElement('div')
      area.classList.add('identifier')
      identifier.appendChild(area)

      this.methodGUICreator.createMethodInput(arg, area, joint[display.name], function (newValue) {
        joint[display.name] = newValue
        view.jointManager.updateEntity(joint)
      })
    }

    view.createButton('Delete', identifier, () => {
      view.jointManager.removeJoint(joint)
    })
  }

  /**
   * Create a view of the cached entities for easy selection
   * @param {*} jointManager an entity Chache object storing all recived or created entities
   */
  displayJoint (jointManager) {
    if (!jointManager) {
      jointManager = this.jointManager
    }
    this.controls.innerHTML = ''

    const overview = jointManager.makeSelectableEntityView((x, y) => {
      this.displayEntity(y, this)
    }, '')

    this.controls.appendChild(overview)

    this.createButton('New', this.controls, () => {
      this.entityManager.addEntity(new JointDataType({
        Name: 'NEW',
        Description: '',
        EntityId: '123456',
        EntityOriginId: '123456',
        IsExternal: false,
        EntityType: 0
      }))
    })
  }

  /**
  * Create some staring joints in the cache so the user has atleast something to choose from
  */
  setupSomeJoints () {
    this.jointManager.addEntity(new JointDataType({
      Name: 'VIN',
      Description: 'This is the Vehicle Identifier Number of the current vehicle',
      EntityId: 'ABCDid000011',
      EntityOriginId: '-',
      IsExternal: true,
    }))
    this.jointManager.addEntity(new JointDataType({
      Name: 'Marriage station',
      Description: 'This is where the chassis and drive unit are joined together',
      EntityId: 'STN125006',
      EntityOriginId: '-',
      IsExternal: true,
    }))
    this.jointManager.addEntity(new JointDataType({
      Name: 'leftwheeljoint',
      Description: 'This is an identifier for a joint on the blueprint',
      EntityId: 'JointABC123',
      EntityOriginId: '12324-23213-13-1231',
      IsExternal: true,
    }))
  }
}
