import { ijtLog } from 'ijt-support/ijt-support.mjs'
import StandardDemo from 'views/standard-demo/standard-demo.mjs'
import JointDemo from 'views/standard-demo/joint-demo.mjs'
import OkRateGraphics from 'views/ok-rate/ok-rate-graphics.mjs'
import TabGenerator from 'views/graphic-support/tab-generator.mjs'
import BasicScreen from 'views/graphic-support/basic-screen.mjs'

class DemoTabsGraphics extends BasicScreen {
  constructor (demoGraphics, jointDemoGraphics, okRateGraphics, currentViewLevel) {
    super('Demos')
    this.tabHelpText = 'Grouped demo tools and result dashboards: Standard Demo, Joint Demo, and OK rate.'
    this.tabGenerator = new TabGenerator(this.backGround, currentViewLevel)

    if (demoGraphics) {
      // Keep Joint Demo as default when available to match previous behavior.
      this.tabGenerator.generateTab(demoGraphics, 1, !jointDemoGraphics)
    }
    if (jointDemoGraphics) {
      this.tabGenerator.generateTab(jointDemoGraphics, 1, true)
    }
    if (okRateGraphics) {
      this.tabGenerator.generateTab(okRateGraphics, 2)
    }
  }

  changeViewLevel (newLevel) {
    if (this.tabGenerator) {
      this.tabGenerator.changeViewLevel(newLevel)
    }
  }

  close () {
    if (this.tabGenerator) {
      this.tabGenerator.close()
    }
  }
}

function createOptionalTab (createFn) {
  try {
    return createFn()
  } catch (error) {
    ijtLog.error(error)
    return null
  }
}

export function createDemoTabs ({
  methodManager,
  resultManager,
  connectionManager,
  addressSpace,
  settings,
  currentViewLevel
}) {
  const demoGraphics = createOptionalTab(() => new StandardDemo(
    methodManager,
    resultManager,
    connectionManager,
    settings
  ))

  const jointDemoGraphics = createOptionalTab(() => new JointDemo(
    methodManager,
    resultManager,
    connectionManager,
    settings
  ))

  const okRateGraphics = createOptionalTab(() => new OkRateGraphics(
    resultManager,
    methodManager,
    addressSpace
  ))

  if (!demoGraphics && !jointDemoGraphics && !okRateGraphics) {
    return null
  }

  return new DemoTabsGraphics(
    demoGraphics,
    jointDemoGraphics,
    okRateGraphics,
    currentViewLevel
  )
}
