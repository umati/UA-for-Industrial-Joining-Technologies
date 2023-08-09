
// import ModelToHTML from './ModelToHTML.mjs'

export default class Serverhandler {
  constructor (container, socket) {
    const backGround = document.createElement('div')
    backGround.classList.add('datastructure')
    container.appendChild(backGround)

    const leftHalf = document.createElement('div')
    leftHalf.classList.add('lefthalf')
    leftHalf.classList.add('scrollableInfoArea')
    backGround.appendChild(leftHalf)

    const serverDiv = document.createElement('div')
    serverDiv.classList.add('myHeader')
    serverDiv.innerText = 'Servers'
    leftHalf.appendChild(serverDiv)

    this.serverArea = document.createElement('ul')
    this.serverArea.classList.add('tightUL')
    leftHalf.appendChild(this.serverArea)

    const rightHalf = document.createElement('div')
    rightHalf.classList.add('righthalf')
    rightHalf.classList.add('scrollableInfoArea')
    backGround.appendChild(rightHalf)

    const comDiv = document.createElement('div')
    comDiv.classList.add('myHeader')
    comDiv.innerText = 'Server status'
    rightHalf.appendChild(comDiv)

    const messageArea = document.createElement('div')
    messageArea.setAttribute('id', 'messageArea')
    rightHalf.appendChild(messageArea)

    this.messages = document.createElement('ul')
    this.messages.setAttribute('id', 'messages')
    messageArea.appendChild(this.messages)
  }

  clearDisplay () {
    this.messages.innerHTML = ''
  }

  // Display a status message from the server
  messageDisplay (msg) {
    let item
    if (msg !== 'keepalive') {
      item = document.createElement('li')
      item.textContent = msg
      this.messages.appendChild(item)
      this.messages.scrollTo(0, this.messages.scrollHeight)
      item.scrollIntoView()
    }
  }

  // Display the different OPC UA servers that the web server suggests
  connectionPoints (msg, socket) {
    function connect (point) {
      document.getElementById('displayedServerName').innerText = point.name
      socket.emit('connect to', point.address)
    }
    this.serverArea.innerHTML = ''
    for (const point of msg) {
      const item = document.createElement('button')
      item.classList.add('myButton')
      item.style.display = 'block'
      item.innerHTML = point.name
      item.onclick = () => {
        connect(point)
      }
      if (point.autoConnect) {
        connect(point)
      }
      this.serverArea.appendChild(item)
      window.scrollTo(0, document.body.scrollHeight)
    }
  }
}
