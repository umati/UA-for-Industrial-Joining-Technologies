import { EntityDataType, EntityTypes } from '../../ijt-support/Models/Entities/EntityDataType.mjs'
import ControlSplitScreen from '../GraphicSupport/ControlSplitScreen.mjs'

export default class EntityCacheView extends ControlSplitScreen {
  constructor (entityManager) {
    super('Identifiers', 'Identifier entities', 'Values')
    this.entityManager = entityManager

    this.setupSomeEntities()

    entityManager.subscribe((allEntities, justAddedEntity) => {
      this.displayEntities()
    })

    this.displayEntities()
  }

  displayEntity (entity, view) {
    const identifier = document.createElement('div')
    view.views.innerHTML = ''
    view.views.appendChild(identifier)

    const displayList = [
      { name: 'name', type: '12' },
      { name: 'entityId', type: '12' },
      { name: 'entityOriginId', type: '12' },
      { name: 'isExternal', type: '1' },
      { name: 'description', type: '12' },
      { name: 'entityType', type: 'DropDown' }
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

      view.createMethodInput(arg, area, entity[display.name], function (newValue) {
        entity[display.name] = newValue
        view.entityManager.updateEntity(entity)
      })
    }

    view.createButton('Delete', identifier, () => {
      view.entityManager.removeEntity(entity)
    })
  }

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
      this.entityManager.addEntity(new EntityDataType(
        'NEW',
        '',
        '123456',
        '123456',
        false,
        0))
    })
  }

  setupSomeEntities () {
    this.entityManager.addEntity(new EntityDataType(
      'VIN',
      'This is the Vehicle Identifier Number of the current vehicle',
      'ABCDid000011',
      '-',
      true,
      Object.values(EntityTypes).findIndex((e) => e === 'vehicle')
    ))
    this.entityManager.addEntity(new EntityDataType(
      'Marriage station',
      'This is where the chassis and drive unit are joined together',
      'STN125006',
      '-',
      true,
      Object.values(EntityTypes).findIndex((e) => e === 'station')
    ))
    this.entityManager.addEntity(new EntityDataType(
      'leftwheeljoint',
      'This is an identifier for a joint on the blueprint',
      '12324-23213-13-1231',
      'leftwheeljointid01',
      true,
      Object.values(EntityTypes).findIndex((e) => e === 'joint')
    ))
  }
}
