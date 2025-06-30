import TabGenerator from '../GraphicSupport/TabGenerator.mjs'
import BasicScreen from 'views/GraphicSupport/BasicScreen.mjs'
import ConfigureLimits from 'views/Envelope/ConfigureLimits.mjs'
import AdviceConfigure from 'views/Envelope/ConfigureAdvice.mjs'
import EnvelopeTrack from 'views/Envelope/EnvelopeTrack.mjs'
/**
 * The purpose of this class is to generate an HTML representation of tightening selection and basic
 * display of a result for OPC UA Industrial Joining Technologies communication
 */
export default class Envelope extends BasicScreen {
  constructor (connectionManager, resultManager, settings) {
    super('Envelope', 'tighteningsystem') // Setting the name of the tab
    this.settings = settings

    const tabGenerator = new TabGenerator(this.backGround, 3)
    this.tabGenerator = tabGenerator

    const envelopeConfigure = new ConfigureLimits(connectionManager, resultManager, settings)
    const adviceConfigure = new AdviceConfigure(connectionManager, resultManager, settings)
    const envelopeTrack = new EnvelopeTrack(connectionManager, resultManager, settings)

    tabGenerator.generateTab(envelopeTrack, 2)
    tabGenerator.generateTab(envelopeConfigure, 2)
    tabGenerator.generateTab(adviceConfigure, 2)

    // Wait until the methods have loaded
    connectionManager.subscribe('methods', (setToTrue) => {
      if (setToTrue) {
        this.activate()
        envelopeConfigure.activate()
        envelopeTrack.activate()
      }
    })
  }

  /**
   * Run everytime the tab is opened
   */
  initiate () {

  }
}
