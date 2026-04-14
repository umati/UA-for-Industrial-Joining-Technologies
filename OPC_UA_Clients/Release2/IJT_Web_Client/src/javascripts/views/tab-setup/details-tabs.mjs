import TabGenerator from 'views/graphic-support/tab-generator.mjs'
import BasicScreen from 'views/graphic-support/basic-screen.mjs'

class DetailsTabsGraphics extends BasicScreen {
  constructor (entityCacheView, assetGraphics, currentViewLevel) {
    super('Details')
    this.tabHelpText = 'Detailed endpoint data views grouped as subtabs, including entities and assets.'
    this.tabGenerator = new TabGenerator(this.backGround, currentViewLevel)

    if (entityCacheView) {
      this.tabGenerator.generateTab(entityCacheView, 3, true)
    }
    if (assetGraphics) {
      this.tabGenerator.generateTab(assetGraphics, 4, !entityCacheView)
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

export function createDetailsTabs ({
  entityCacheView,
  assetGraphics,
  currentViewLevel
}) {
  if (!entityCacheView && !assetGraphics) {
    return null
  }

  return new DetailsTabsGraphics(
    entityCacheView,
    assetGraphics,
    currentViewLevel
  )
}
