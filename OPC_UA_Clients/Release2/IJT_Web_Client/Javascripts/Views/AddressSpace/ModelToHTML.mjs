/**
 * The purpose of this class is to take a model and make a HTML representation
 * of it where a user can expand subsections to view more data
 * (used to display on the right column)
 */
export default class ModelToHTML {
  constructor (messageArea) {
    this.messageArea = messageArea
    this.longVersionOuter = null // This contains the HTML representation in detail
    this.shortVersion = null // This contains the HTML representation in brief
  }

  toHTML (model, brief = true, parentName) {
    function toggler (shortVersion, longVersionOuter) {
      // Eventhandlers to handle expanding or shrinking the HTML representation
      // of a complex value
      longVersionOuter.addEventListener('click', (e) => {
        if (!e) e = window.event
        e.cancelBubble = true
        if (e.stopPropagation) e.stopPropagation()
        longVersionOuter.style.display = 'none'
        shortVersion.style.display = 'block'
      }, false)
      shortVersion.addEventListener('click', (e) => {
        if (!e) e = window.event
        e.cancelBubble = true
        if (e.stopPropagation) e.stopPropagation()
        longVersionOuter.style.display = 'block'
        shortVersion.style.display = 'none'
      }, false)
    }

    if (model.constructor.name === 'DefaultNode' && model.value && model.value.value != null) {
      let result = ''
      if (typeof model.value.value === 'string' || typeof model.value.value === 'number') {
        result = `${model.displayName.text} = ${model.value.value}`
      } else if (model.value.value.text && typeof model.value.value.text === 'string') {
        result = `${model.displayName.text} = ${model.value.value.text}`
      }
      const combined = document.createElement('li')
      combined.innerText = result
      // print associations and components
      return combined
    }

    // Seting up the HTML containers for expanded or shrunken complex value
    const combined = document.createElement('li')
    const shortVersion = document.createElement('li')
    shortVersion.style.display = 'block'
    const longVersionOuter = document.createElement('li')
    longVersionOuter.style.display = 'none'
    const longVersion = document.createElement('li')
    longVersion.classList.add('indent')

    let abbreviation = ''
    if (model.constructor.name === 'LocalizationModel') {
      abbreviation = ' : ' + model.Text + ' '
    } else if (model.constructor.name === 'NodeId') {
      abbreviation = ' : [' + model.stringify() + '] '
    }

    if (parentName) {
      const ownerName = document.createElement('li')
      const ownerName2 = document.createElement('li')
      ownerName.innerHTML = parentName + abbreviation + ' &#9655'
      ownerName2.innerHTML = parentName + ' &#9661'
      shortVersion.appendChild(ownerName)
      longVersionOuter.appendChild(ownerName2)
    }

    // Tie the eventhandlers to the expanded or shrunken complex value
    toggler(shortVersion, longVersionOuter)

    // combine the expanded or shrunken complex value
    combined.appendChild(shortVersion)
    longVersionOuter.appendChild(longVersion)
    combined.appendChild(longVersionOuter)
    combined.longVersionOuter = longVersionOuter
    combined.shortVersion = shortVersion
    combined.expandLong = function () { // This is used to get the initial display expanded
      if (this.longVersionOuter && this.shortVersion) {
        this.longVersionOuter.style.display = 'block'
        this.shortVersion.style.display = 'none'
      }
    }

    const nameTag = document.createElement('li')
    let name = model.DisplayName?.text
    if (!name) {
      name = model.BrowseName?.name
    }
    if (!name) {
      name = model.Name
    }
    if (!name) {
      name = model.EventId
    }
    if (name) {
      nameTag.innerText = name
      nameTag.classList.add('textHeader')
      longVersion.appendChild(nameTag)
    }
    // Loop over the model object and handle diffrent types of values
    // such as arrays, nesting
    for (const [key, value] of Object.entries(model)) {
      // console.log(`${key}: ${value}`)
      if (!value || key === 'parent') {
        /* Do nothing for parents */
      } else if (!value || key === 'data_types') {
        /* Do nothing for data_types since the structure can't easily be parsed */
      } else if (key === 'relations') {
        // console.log('Relation values: ' + value)
        for (const [relationName, relationItems] of Object.entries(value)) {
          for (const associationValue of Object.values(relationItems)) {
            const associationItem = document.createElement('li')
            associationItem.innerText = relationName + ': ' + associationValue.browseName.name
            longVersion.appendChild(associationItem)
          }
        }
      } else if (Array === value.constructor) {
        // Handle an array of values (that may be complex values)
        const outerList = document.createElement('li')
        longVersion.appendChild(outerList)
        const ownerName = document.createElement('li')
        ownerName.innerHTML = key + '(' + value.length + ') &#9655'
        outerList.appendChild(ownerName)

        const item = document.createElement('li')
        const ind = document.createElement('li')
        item.style.display = 'none'
        const ownerName2 = document.createElement('li')
        ownerName2.innerHTML = key + '&#9661'
        ind.classList.add('indent')
        item.appendChild(ownerName2)
        item.appendChild(ind)
        outerList.appendChild(item)

        toggler(ownerName, item)

        let i = 0
        for (const v of value) {
          if (typeof v === 'object') {
            const obj = this.toHTML(v, brief, '[' + i + ']')
            ind.appendChild(obj)
          } else {
            const li = document.createElement('li')
            li.innerHTML = v
            ind.appendChild(li)
          }
          i++
        }
      } else if (typeof value === 'object' && key !== 'debugValues' && value.type !== 'linkedValue') {
        // Here recursion is used to handle nested complex values
        // console.log('Key: '+key)
        const item = this.toHTML(value, brief, key)

        longVersion.appendChild(item)
      } else if (typeof value === 'object' && key !== 'debugValues' && value.type === 'linkedValue') {
        // Here linked objects are displayed
        const item = document.createElement('li')
        item.textContent = `${key}: ${value.value}`
      } else if (key !== 'debugValues') {
        // This handles the most simple type of name-value pair
        const item = document.createElement('li')
        item.textContent = `${key}: ${value}`
        longVersion.appendChild(item)
      }
    }
    if (shortVersion.innerHTML === '') {
      shortVersion.appendChild(longVersion.children[0].cloneNode())
    }
    return combined
  }

  /**
 * this function takes a recieved object from the webclient and tries to create resonable HTML.
 * NOTE: This is not meant to handle a true Model, just the JSON representation. Most often
 * You start from the actual model instead of the JSON and use the toHTML() above instead.
 * This function is only for when you want to show something before the model has been created.
 * @param {} recievedObject a JSON representation of what was recieved
 * @param {*} startText The first part of the row (likely the call type)
 */
  display (recievedObject, startText = 'Response') {
    let onScreen
    if (typeof recievedObject === 'object') { // Handle a model
      const onScreen = this.toHTML(recievedObject, true, startText)
      if (onScreen.expandLong) {
        onScreen.expandLong()
      }
      // var item = document.createElement('li')
      // item.textContent = `${msg.dataValue.serverTimestamp}`
      // messages.appendChild(item)

      this.messageArea.appendChild(onScreen)
      this.messageArea.scrollTo(0, this.messageArea.scrollHeight)
      onScreen.scrollIntoView()
    } else { // Handle a single value
      onScreen = document.createElement('li')

      onScreen.innerHTML = startText + ' ' + this.prettyPrint(JSON.parse(recievedObject))

      this.messageArea.appendChild(onScreen)
      this.messageArea.scrollTo(0, this.messageArea.scrollHeight)
      onScreen.scrollIntoView()
    }
  }

  prettyPrint (obj, indent = '&nbsp;&nbsp;&nbsp;') {
    if (obj === '{}' || obj === null) {
      return ''
    } else if (typeof obj === 'string' || obj instanceof String) {
      return obj
    } else if (obj.length > 0) {
      let result = '['
      for (const member of obj) {
        result += '<br>' + indent + this.prettyPrint(member, indent + '&nbsp;&nbsp;&nbsp;')
      }
      return result + ']'
    } else if (obj.pythonclass === 'LocalizedText') {
      return obj.Text
    } else {
      let typeOfClass = ''
      let result = '<br>' + indent + '{'
      for (const [key, value] of Object.entries(obj)) {
        if (key === 'pythonclass') {
          typeOfClass = value
        } else {
          result += '<br>' + indent + key + ': ' + this.prettyPrint(value, indent + '&nbsp;&nbsp;&nbsp;')
        }
      }
      return '+' + typeOfClass + '+ ' + result + '<br>' + indent + '}'
    }
  }
}
