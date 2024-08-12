import { EntityDataType, EntityTypes } from '../../ijt-support/Models/Entities/EntityDataType.mjs'
import ControlSplitScreen from '../GraphicSupport/ControlSplitScreen.mjs'
import MethodGUICreator from '../Methods/MethodGUICreator.mjs'

export default class EntityCacheView extends ControlSplitScreen {
  constructor (entityManager) {
    super('Entities', 'Identifier entities', 'Values')
    this.entityManager = entityManager
    this.methodGUICreator = new MethodGUICreator(this, null, entityManager, null)

    this.setupSomeEntities()

    entityManager.subscribe((allEntities, justAddedEntity) => {
      this.displayEntities()
    })

    this.displayEntities()
  }

  /**
   * Display a specific Entity for editing
   * @param {*} entity The entity that should be edited
   * @param {*} view The background view object inheriting the BaseScreen functionality
   */
  displayEntity (entity, view) {
    const identifier = document.createElement('div')
    view.views.innerHTML = ''
    view.views.appendChild(identifier)

    const displayList = [
      { name: 'EntityType', type: 'DropDown' },
      { name: 'EntityId', type: '12' },
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
        },
        Options: EntityTypes
      }

      const area = document.createElement('div')
      area.classList.add('identifier')
      identifier.appendChild(area)

      this.methodGUICreator.createMethodInput(arg, area, entity[display.name], function (newValue) {
        entity[display.name] = newValue
        view.entityManager.updateEntity(entity)
      })
    }

    view.createButton('Delete', identifier, () => {
      view.entityManager.removeEntity(entity)
    })
  }

  /**
   * Create a view of the cached entities for easy selection
   * @param {*} entityCache an entity Chache object storing all recived or created entities
   */
  displayEntities (entityCache) {
    if (!entityCache) {
      entityCache = this.entityManager
    }
    this.controls.innerHTML = ''

    const overview = entityCache.makeSelectableEntityView((x, y) => {
      this.displayEntity(y, this)
    }, '')

    this.controls.appendChild(overview)

    this.createButton('New', this.controls, () => {
      this.entityManager.addEntity(new EntityDataType({
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
  * Create some staring entities in the cache so the user has atleast something to choose from
  */
  setupSomeEntities () {
    this.entityManager.addEntity(new EntityDataType({
      Name: 'VIN',
      Description: 'This is the Vehicle Identifier Number of the current vehicle',
      EntityId: 'ABCDid000011',
      EntityOriginId: '-',
      IsExternal: true,
      EntityType: Object.values(EntityTypes).findIndex((e) => e === 'vehicle')
    }))
    this.entityManager.addEntity(new EntityDataType({
      Name: 'Marriage station',
      Description: 'This is where the chassis and drive unit are joined together',
      EntityId: 'STN125006',
      EntityOriginId: '-',
      IsExternal: true,
      EntityType: Object.values(EntityTypes).findIndex((e) => e === 'station')
    }))
    this.entityManager.addEntity(new EntityDataType({
      Name: 'leftwheeljoint',
      Description: 'This is an identifier for a joint on the blueprint',
      EntityId: 'JointABC123',
      EntityOriginId: '12324-23213-13-1231',
      IsExternal: true,
      EntityType: Object.values(EntityTypes).findIndex((e) => e === 'joint')
    }))
  }
}
