import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'
/**
 * The purpose of this class is to encapsulate the code resposnible for the HTML representation of method
 * invocations in OPC UA Industrial Joining Technologies
 */
export default class MethodGraphics extends ControlMessageSplitScreen {
  constructor (container) {
    super(container, 'Methods', 'Call results')
    this.container = container
  }

  initiate () {
    // run everytime the tab is opened
  }

  /**
  * Turns the surounding border yellow when all is set up correctly
  * @param {*} method The method that should be turned yellow
  */
  activate (method) {
    method.container.style.borderColor = 'yellow'
  }

  /**
   * Makes it easier to create a button for method invokation
   * @param {*} method is the method that should have the button
   */
  createMethodButton (method) {
    this.createButton(method.name, method.container, () => {
      method.callMethod()
    })
  }

  /**
   * Simplify how an input field for method invokation is created and used
   * @param {*} title the name of input field in the GUI
   * @param {*} method the method that needs input
   * @param {*} initialValue The value that initially should be in the field
   * @returns a function that tells the value in the input field
   */
  createMethodInput (title, method, initialValue) {
    return this.createInput(title, method.container, initialValue)
  }
}
