/**
 * Description placeholder
 *
 * @class Selection
 * @typedef {Selection}
 */
class Selection {
  constructor (refreshCallback) {
    this.limits = []
    this._name = 'ABC'
    this._nameElement = null
    this._resultElement = null
    this.refreshCallback = refreshCallback
  }

  get name () {
    return this._name
  }

  set name (newName) {
    this._name = newName
    if (this._nameElement) {
      this._nameElement.value = newName
      if (this.refreshCallback) {
        this.refreshCallback(this)
      }
    }
  }

  check (value) {
    return false
  }

  addLimit (limit) {
    this.limits.push(limit)
  }

  getResultValue (result) {
    return false
  }

  generateInputHTML (context, screen) {
    const selectionArea = screen.createArea('Selection parameters')
    selectionArea.style.border = '2px solid red'
    context.appendChild(selectionArea)
    const topArea = screen.createArea('')
    topArea.style.border = '2px solid green'
    this._nameElement = screen.createInput(this.name, null, (inputValue) => {
      this.name = inputValue
    })

    screen.createTitledInput(
      'Name',
      this._nameElement,
      topArea
    )
    topArea.appendChild(this._nameElement)
    selectionArea.appendChild(topArea)

    return selectionArea
  }
}

/**
 * Description placeholder
 *
 * @class Selection
 * @typedef {Selection}
 */
class SingleValueSelection extends Selection {
  constructor (value = '') {
    super()
    this._value = value
  }

  get value () {
    return this._value
  }

  set value (val) {
    this._value = val
  }

  check (result) {
    return this.getResultValue(result) >= this.value
  }

  generateInputHTML (context, screen) {
    const area = super.generateInputHTML(context, screen)

    const typeName = this.constructor.displayText

    screen.createTitledInput(
      typeName,
      screen.createInput(this.value, null, (inputValue) => {
        this.value = inputValue
        this.name = typeName + ' ' + this.value
      }),
      area
    )

    return area
  }
}

/**
 * Description placeholder
 *
 * @class Selection
 * @typedef {Selection}
 */
class SingleAssociatedEntitySelection extends SingleValueSelection {
  constructor (value = '', associatedType) {
    super(value)
    this.associatedType = associatedType // Associated entity type for Program
  }

  check (result) {
    return this.getEntityId(result) === this.value
  }

  getEntityId (result) {
    const entity = this.getEntityType(result, this.associatedType)
    if (entity) {
      return entity.EntityId
    }
  }

  getEntityType (result, nr) {
    for (const entity of result.ResultMetaData.AssociatedEntities) {
      if (parseInt(entity.EntityType) === parseInt(nr)) {
        return entity
      }
    }
  }

  getResultValue (result) {
    return this.getEntityId(result, this.associatedType)
  }
}

export class SelectTighteningProgramOriginId extends SingleAssociatedEntitySelection {
  constructor (value) {
    super(value, 27)
  }

  static displayText = 'Program'
}

export class SelectJoint extends SingleValueSelection {
  constructor (value = '') {
    super(value, 23)
  }

  static displayText = 'Joint'
}

export class SelectBolt extends SingleValueSelection {
  constructor (value = '') {
    super(value, 13) // this is wrong. bolt is not listed yet
  }

  static displayText = 'Bolt'
}

export class SelectPart extends SingleValueSelection {
  constructor (value = '') {
    super(value, 22) // this is wrong. bolt is not listed yet
  }

  static displayText = 'Part'
}

export class SelectVirtualMachine extends SingleValueSelection {
  constructor (value = '') {
    super(value, 41)
  }

  static displayText = 'Virtual Station'
}

export class SelectController extends SingleValueSelection {
  constructor (value = '') {
    super(value, 3)
  }

  static displayText = 'Controller'
}

export class SelectTool extends SingleAssociatedEntitySelection {
  constructor (value = '') {
    super(value, 4)
  }

  static displayText = 'ToolId'
}

export class SelectVIN extends SingleAssociatedEntitySelection {
  constructor (value = '') {
    super(value, 20)
  }

  static displayText = 'VIN'
}

export class SelectPIN extends SingleAssociatedEntitySelection {
  constructor (value = '') {
    super(value, 21)
  }

  static displayText = 'PIN'
}

export class SelectStation extends SingleAssociatedEntitySelection {
  constructor (value = '') {
    super(value, 36)
  }

  static displayText = 'Station'
}

export class SelectChannel extends SingleAssociatedEntitySelection {
  constructor (value = '') {
    super(value, 35)
  }

  static displayText = 'Channel'
}

export class SelectLine extends SingleAssociatedEntitySelection {
  constructor (value = '') {
    super(value, 37)
  }

  static displayText = 'Production Line'
}

export class SelectLocation extends SingleAssociatedEntitySelection {
  constructor (value = '') {
    super(value, 38)
  }

  static displayText = 'Location'
}

export class SelectUser extends SingleAssociatedEntitySelection {
  constructor (value = '') {
    super(value, 39)
  }

  static displayText = 'User'
}

export class SelectAll extends Selection {
  static displayText = 'All'

  check (result) {
    return true
  }

  generateInputHTML (context, screen) {
    const area = super.generateInputHTML(context, screen)
    this.name = 'All'
    return area
  }
}

export class SelectAND extends Selection {
  constructor (selection1, selection2) {
    super()
    this.selection1 = selection1
    this.selection2 = selection2
  }

  static displayText = 'AND'

  get value () {
    return false
  }

  set value (val) {
    throw new Error('No value in AND')
  }

  check (result) {
    return this.selection1.check(result) && this.selection2.check(result)
  }

  generateInputHTML (context, screen) {
    const area = super.generateInputHTML(context, screen)

    const selection1Name = this.selection1?.name || ''
    const selection2Name = this.selection2?.name || ''

    screen.createTitledInput(
      'Selection 1',
      screen.createInput(selection1Name, null, (value) => {
        this.selection1 = value
        this.name = SelectController.displayText + ' ' + this.selection1?.name +
        ' AND ' + this.selection2?.name
      }),
      area
    )

    screen.createTitledInput(
      'Selection 2',
      screen.createInput(selection2Name, null, (value) => {
        this.selection1 = value
        this.name = SelectController.displayText + ' ' + this.selection1.name +
        ' AND ' + this.selection2.name
      }),
      area
    )

    return area
  }
}

export class SelectNOT extends Selection {
  constructor (selection1) {
    super()
    this.selection1 = selection1
  }

  static displayText = 'NOT'

  get value () {
    return this.selection1
  }

  set value (val) {
    this.selection1 = val
  }

  check (result) {
    return !this.selection1.check(result)
  }

  generateInputHTML (context, screen) {
    const area = super.generateInputHTML(context, screen)

    const selection1Name = this.selection1?.name || ''

    screen.createTitledInput(
      'Selection 1',
      screen.createInput(selection1Name, null, (value) => {
        this.selection1 = value
        this.name = SelectController.displayText + ' ' + this.selection1.name +
        ' AND ' + this.selection2.name
      }),
      area
    )

    return area
  }
}
