import { EntityTypes } from '../Models/Entities/EntityDataType.mjs'

/**
 * The purpose of this class is to
 *
 */
export class EntityCache {
  constructor () {
    this.cache = {}
    this.callbacks = []
    this.entityTypes = EntityTypes
  }

  subscribe (callback) {
    this.callbacks.push(callback)
  }

  addEntity (entity) {
    if (this.getEntityFromId(entity.EntityType, entity.EntityId)) {
      return
    }
    const currentList = this.cache[entity.EntityType]
    if (currentList) {
      currentList.push(entity)
    } else {
      this.cache[entity.EntityType] = [entity]
    }
    for (const callback of this.callbacks) {
      callback(this.cache, entity)
    }
  }

  removeEntity (entity) {
    for (let t = 0; t < Object.values(this.cache).length; t++) {
      const key = Object.keys(this.cache)[t]
      const values = Object.values(this.cache)[t]
      const filteredValues = values.filter((e) => { return e.EntityId !== entity.EntityId })
      this.cache[key] = filteredValues
    }
    for (const callback of this.callbacks) {
      callback(this.cache, entity)
    }
  }

  getEntityFromId (entityType, id) {
    const t = this.cache[entityType]
    if (!t) {
      return
    }
    const f = t.filter((e) => { return e.EntityId === id })
    if (f.length === 1) {
      return f[0]
    }
  }

  updateEntity (entity) {
    this.removeEntity(entity)
    this.addEntity(entity)
  }

  makeSelectableEntityView (onselect, title) {
    const backGround = document.createElement('div')
    const label = document.createElement('label')
    label.innerText = title
    backGround.appendChild(label)
    for (let i = 0; i < Object.values(this.cache).length; i++) {
      const key = Object.keys(this.cache)[i]
      const values = Object.values(this.cache)[i]
      if (values.length > 0) {
        const area = document.createElement('div')
        area.classList.add('identifierType')
        area.innerHTML = EntityTypes[key]
        backGround.appendChild(area)
        for (const entity of values) {
          const identifier = document.createElement('div')
          identifier.classList.add('identifier')
          area.appendChild(identifier)
          identifier.innerHTML = entity.Name
          // identifier.entityData = entity
          identifier.entityDisplay = this.displayEntity
          // identifier.entityView = this
          identifier.onclick = function (a) {
            onselect(a, entity)
          }
        }
      }
    }
    return backGround
  }
}
