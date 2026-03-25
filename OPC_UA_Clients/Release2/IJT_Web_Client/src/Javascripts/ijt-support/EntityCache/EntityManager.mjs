import { EntityTypes } from '../Models/Entities/EntityDataType.mjs'

/**
 * EntityCache — stores and indexes OPC UA entity nodes by type.
 *
 * Entities are grouped by EntityType (numeric key) in a plain object cache.
 * All mutations notify subscribers with the full cache and the changed entity.
 */
export class EntityCache {
  constructor () {
    /** @type {Object.<number, object[]>} */
    this.cache = {}
    /** @type {Function[]} */
    this.callbacks = []
    this.entityTypes = EntityTypes
  }

  /**
   * Register a callback invoked after every cache mutation.
   * @param {(cache: object, entity: object) => void} callback
   */
  subscribe (callback) {
    this.callbacks.push(callback)
  }

  /**
   * Add an entity to the cache (no-op if already present by type+id).
   * @param {object} entity
   */
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
    this._notify(entity)
  }

  /**
   * Remove all entries with a matching EntityId (across all types).
   * @param {object} entity
   */
  removeEntity (entity) {
    for (const [key, values] of Object.entries(this.cache)) {
      this.cache[key] = values.filter((e) => e.EntityId !== entity.EntityId)
    }
    this._notify(entity)
  }

  /**
   * Look up an entity by type and id.
   * @param {number} entityType
   * @param {string} id
   * @returns {object|undefined}
   */
  getEntityFromId (entityType, id) {
    const list = this.cache[entityType]
    if (!list) return undefined
    return list.find((e) => e.EntityId === id)
  }

  /**
   * Replace an entity by removing the old entry and re-adding the updated one.
   * @param {object} entity
   */
  updateEntity (entity) {
    this.removeEntity(entity)
    this.addEntity(entity)
  }

  /**
   * Build a DOM element listing selectable entities grouped by type.
   * @param {Function} onselect  callback(event, entity) when an entity is clicked
   * @param {string}   title     label shown above the list
   * @returns {HTMLElement}
   */
  makeSelectableEntityView (onselect, title) {
    const backGround = document.createElement('div')
    const label = document.createElement('label')
    label.textContent = title
    backGround.appendChild(label)
    for (const [key, values] of Object.entries(this.cache)) {
      if (values.length === 0) continue
      const area = document.createElement('div')
      area.classList.add('identifierType')
      area.textContent = EntityTypes[key] ?? key
      backGround.appendChild(area)
      for (const entity of values) {
        const identifier = document.createElement('div')
        identifier.classList.add('identifier')
        identifier.textContent = entity.Name
        identifier.onclick = (a) => onselect(a, entity)
        area.appendChild(identifier)
      }
    }
    return backGround
  }

  /** @private */
  _notify (entity) {
    for (const callback of this.callbacks) {
      try {
        callback(this.cache, entity)
      } catch (err) {
        console.error('EntityCache subscriber threw:', err)
      }
    }
  }
}
