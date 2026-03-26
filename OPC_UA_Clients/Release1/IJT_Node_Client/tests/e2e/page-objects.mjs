export class ConnectionPage {
  constructor (page) {
    this.page = page
  }

  async navigate () {
    await this.page.goto('/')
  }

  get endpointInput () {
    return this.page.locator('input[type="text"]').first()
  }

  get connectButton () {
    return this.page.locator('button').filter({ hasText: /connect/i }).first()
  }
}

export class TabPage {
  constructor (page, tabName) {
    this.page = page
    this.tabName = tabName
  }

  get tab () {
    return this.page.locator(`[role="tab"], .tab, li`).filter({ hasText: this.tabName }).first()
  }

  async clickTab () {
    await this.tab.click()
  }
}
