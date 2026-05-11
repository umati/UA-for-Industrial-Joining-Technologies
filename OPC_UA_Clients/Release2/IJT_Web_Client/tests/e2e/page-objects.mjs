/**
 * Page Object Model (POM) for the IJT Web Client.
 *
 * Every view in the application gets its own class. All Playwright
 * locators are defined here — never hard-code selectors in spec files.
 *
 * Usage:
 *   import { AppPage, MethodsPage, EventsPage, ... } from './page-objects.mjs'
 */

// ─────────────────────────────────────────────────────────────────────────────
// Selector constants — single source of truth for every CSS class / value
// ─────────────────────────────────────────────────────────────────────────────
function cssAttr (value) {
  return String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"')
}

export const SEL = {
  // Navigation
  MAIN_DROPDOWN: 'select.mainDropDown',
  SETTINGS_SCREEN: '.settingsScreen',
  TAB_BUTTON: (name) => `input.tabButton[value="${name}"]`,
  ENDPOINT_STATE: (name, state, value) => `input.tabButton[value="${name}"][data-opcua-${state}-state="${value}"]`,

  // Connection status bar
  STATUS_LABEL: (text) => `.connection-label:has-text("${text}")`,
  ON_COLOR: '.onColor',
  OFF_COLOR: '.offColor',

  // Methods view
  METHOD_AREA: '.methodBorder',
  METHOD_CALL_BTN: 'button:has-text("Call")',

  // Events view
  MESSAGES_LIST: '.messages',
  MESSAGE_ITEMS: '.messages li',
  TOGGLE_QUEUE_BTN: 'button:has-text("Toggle queueing")',
  NEXT_EVENT_BTN: 'button:has-text("Next event")',

  // Consolidated Result view
  RESULT_HEADER: '.resultheader',
  RESULT_TYPE_SELECT: '.resultheader select[data-ijt-result-control="type"]',
  RESULT_ITEM_SELECT: '.resultheader select[data-ijt-result-control="result"]',
  RESULT_IMPORT_MODE_SELECT: '.resultImportMode select',
  RESULT_IMPORT_STRICT_CHECKBOX: '.resultImportStrictInput',
  RESULT_IMPORT_FILE_INPUT: '.resultImportInput',
  RESULT_IMPORT_BUTTON: 'button:has-text("Import")',
  RESULT_EXPORT_BUTTON: 'button:has-text("Export")',
  RESULT_STATUS: '.consolidatedResultScreen .uiStatus',
  DRAW_BOX: '.drawResultBox',
  COMPLE_WRAPPER: '.complewrapper',
  RES_TIGHTENING: '.resTightening',
  RES_JOB: '.resJob',
  RES_BATCH: '.resBatch',
  RES_NOK: '.resNOK',

  // Joint Demo view
  DEMO_SELECT_JOINT1: '.demoActionSelectJoint1',
  DEMO_SELECT_JOINT2: '.demoActionSelectJoint2',
  DEMO_SIMULATE_TIGHTEN: '.demoActionSimulateTightening',
  DEMO_MAIN_AREA: '.demoMainArea',
  DEMO_ACTIVE_URI: '.jointDemoActiveUriLabel',

  // OK Rate view
  OK_RATE_VIEW: '.okRateView',
  OK_RATE_VALUE: '.okRateValue',
  OK_RATE_STAT: '.okRateStat',
  OK_RATE_SIMULATE_OK: 'button:has-text("Simulate OK result")',
  OK_RATE_SIMULATE_NOK: 'button:has-text("Simulate NOT OK result")',
  OK_RATE_CLEAR: 'button:has-text("Clear counters")',

  // Address Space view
  TREE_BUTTON: '.treeButton',
  TREE_BUTTON_BY_BROWSE_NAME: (name) => `button.treeButton[data-opcua-browse-name="${cssAttr(name)}"]`,
  TREE_BUTTON_BY_NODE_ID: (nodeId) => `button.treeButton[data-opcua-node-id="${cssAttr(nodeId)}"]`,
  BUTTON_AREA: '.buttonArea',

  // Servers view
  SERVER_ROW: '.serverRow',
  SERVER_ROWS: '.serversRows',
  SERVER_ADD_BTN: 'button:has-text("Add new server")',
  SERVER_SAVE_BTN: 'button:has-text("Save")',

  // Assets view
  ASSET_BOX: '.drawAssetBox',

  // Joints / Entities view
  ENTITY_NEW_BTN: 'button:has-text("New")',
  ENTITY_DELETE_BTN: 'button:has-text("Delete")',

}

// Result type codes (matches server-side classification)
export const RESULT_TYPE = {
  LATEST: '-1',
  OTHER: '0',
  TIGHTENING: '1',
  BATCH: '3',
  JOB: '4',
}

// View levels in the main dropdown
export const VIEW_LEVEL = {
  BASIC: '1',
  SIMPLE: '2',
  DETAILED: '3',
  SPECIALIZED: '4',
  SETTINGS: '5',
}

// ─────────────────────────────────────────────────────────────────────────────
// AppPage — top-level page helper
// ─────────────────────────────────────────────────────────────────────────────
export class AppPage {
  constructor (page, appUrl = '/') {
    this.page = page
    this.appUrl = appUrl
  }

  /** Navigate to the app root and wait for basic render. */
  async goto () {
    await this.page.goto(this.appUrl)
    await this.page.waitForLoadState('domcontentloaded')
    // Give JS time to bootstrap
    await this.page.waitForTimeout(500)
  }

  /** Switch the main view-level dropdown (1=Basic … 5=Settings). */
  async setViewLevel (level) {
    await this.page.selectOption(SEL.MAIN_DROPDOWN, level)
    if (String(level) === '5') {
      await this.page.locator(SEL.SETTINGS_SCREEN).waitFor({ state: 'visible', timeout: 5_000 })
      return
    }
    await this.page.waitForFunction(
      ([selector, expected]) => document.querySelector(selector)?.value === expected,
      [SEL.MAIN_DROPDOWN, level],
      { timeout: 5_000 }
    )
  }

  /** Click a top-level tab by its display name. */
  async clickTab (tabName, { timeout = 30_000 } = {}) {
    const tab = this.page.locator(SEL.TAB_BUTTON(tabName)).first()
    await tab.waitFor({ state: 'visible', timeout })
    await tab.click()
    await this.page.waitForFunction(
      (selector) => document.querySelector(selector)?.getAttribute('aria-selected') === 'true',
      SEL.TAB_BUTTON(tabName),
      { timeout }
    )
  }

  /** Connect to the LOCAL server endpoint tab. */
  async connectToLocal ({ timeout = 90_000 } = {}) {
    await this.clickTab('LOCAL', { timeout })
    await this.page.locator(SEL.ENDPOINT_STATE('LOCAL', 'connection', 'connected'))
      .first()
      .waitFor({ state: 'visible', timeout })
    await this.page.locator(SEL.ENDPOINT_STATE('LOCAL', 'subscription', 'connected'))
      .first()
      .waitFor({ state: 'visible', timeout })
  }

  /** Assert the page title matches the expected pattern. */
  async expectTitle (pattern = /OPC UA IJT Demo/) {
    await this.page.waitForFunction(
      (pat) => new RegExp(pat).test(document.title),
      pattern.source,
      { timeout: 10_000 }
    )
  }

  /** Return the methods page helper (switches to Methods tab). */
  async openMethods () {
    await this.clickTab('Methods')
    return new MethodsPage(this.page)
  }

  async openEvents () {
    await this.clickTab('Events')
    return new EventsPage(this.page)
  }

  async openResults () {
    await this.clickTab('Demos')
    await this.clickTab('Consolidated Result')
    return new ResultsPage(this.page)
  }

  async openJointDemo () {
    await this.clickTab('Demos')
    await this.clickTab('Joint Demo')
    return new JointDemoPage(this.page)
  }

  async openOkRate () {
    await this.clickTab('Demos')
    await this.clickTab('OK rate')
    return new OkRatePage(this.page)
  }

  async openAddressSpace () {
    await this.clickTab('Address Space')
    return new AddressSpacePage(this.page)
  }

  async openServers () {
    await this.clickTab('Servers')
    return new ServersPage(this.page)
  }

  async openAssets () {
    await this.clickTab('Assets')
    return new AssetsPage(this.page)
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// ConnectionStatusBar
// ─────────────────────────────────────────────────────────────────────────────
export class ConnectionStatusBar {
  constructor (page) {
    this.page = page
  }

  async waitForConnected ({ timeout = 60_000 } = {}) {
    await this.page.locator(SEL.ON_COLOR).first().waitFor({ state: 'visible', timeout })
  }

  async isAnyStatusOn () {
    return (await this.page.locator(SEL.ON_COLOR).count()) > 0
  }

  async isAnyStatusOff () {
    return (await this.page.locator(SEL.OFF_COLOR).count()) > 0
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// MethodsPage
// ─────────────────────────────────────────────────────────────────────────────
export class MethodsPage {
  constructor (page) {
    this.page = page
  }

  /** Wait for at least one method area to appear. */
  async waitForMethods ({ timeout = 90_000 } = {}) {
    await this.page.locator(SEL.METHOD_AREA).first().waitFor({ state: 'visible', timeout })
  }

  /** Find a method area that contains a label matching any of the given names. */
  async findMethodArea (nameOrAliases) {
    const names = Array.isArray(nameOrAliases) ? nameOrAliases : [nameOrAliases]
    for (const name of names) {
      const area = this.page
        .locator(SEL.METHOD_AREA)
        .filter({ has: this.page.locator('label', { hasText: name }) })
        .first()
      if ((await area.count()) > 0) return { area, name }
    }
    return null
  }

  /** Click the Call button for the first matching method area. */
  async callMethod (nameOrAliases, { waitMs = 500 } = {}) {
    const found = await this.findMethodArea(nameOrAliases)
    if (!found) throw new Error(`Method not found: ${JSON.stringify(nameOrAliases)}`)
    await found.area.locator(SEL.METHOD_CALL_BTN).first().click()
    if (waitMs > 0) await this.page.waitForTimeout(waitMs)
    return found.name
  }

  /** Return all visible method area labels. */
  async getMethodNames () {
    const areas = this.page.locator(SEL.METHOD_AREA)
    const count = await areas.count()
    const names = []
    for (let i = 0; i < count; i++) {
      const label = await areas.nth(i).locator('label').first().textContent()
      if (label) names.push(label.trim())
    }
    return names
  }

  /** Simulate all four standard IJT simulation methods in sequence. */
  async runAllSimulations () {
    await this.callMethod(['SimulateSingleResult'], { waitMs: 800 })
    await this.callMethod(['SimulateJobResult'], { waitMs: 800 })
    await this.callMethod([
      'Simulate_Batch_or_SYNC_Result',
      'SimulateBatch_Or_Sync_Result',
      'SimulateBatchOrSyncResult',
    ], { waitMs: 800 })
    await this.callMethod(['SimulateEvents', 'SimualteEvents'], { waitMs: 800 })
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// EventsPage
// ─────────────────────────────────────────────────────────────────────────────
export class EventsPage {
  constructor (page) {
    this.page = page
  }

  async waitForEvents ({ minCount = 1, timeout = 60_000 } = {}) {
    await this.page.waitForFunction(
      ([sel, min]) => document.querySelectorAll(sel).length >= min,
      ['.messages li', minCount],
      { timeout }
    )
  }

  async getEventCount () {
    return this.page.locator(SEL.MESSAGE_ITEMS).count()
  }

  async getAllEventText () {
    return this.page.locator(SEL.MESSAGES_LIST).innerText()
  }

  /** Returns true if any event item contains the given substring. */
  async hasEventContaining (text) {
    const items = this.page.locator(SEL.MESSAGE_ITEMS)
    const count = await items.count()
    for (let i = 0; i < count; i++) {
      const t = await items.nth(i).textContent()
      if (t?.includes(text)) return true
    }
    return false
  }

  async toggleQueue () {
    await this.page.locator(SEL.TOGGLE_QUEUE_BTN).first().click()
    await this.page.waitForTimeout(200)
  }

  async clickNextEvent () {
    const btn = this.page.locator(SEL.NEXT_EVENT_BTN).first()
    if ((await btn.count()) > 0) {
      await btn.click()
      await this.page.waitForTimeout(200)
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// ResultsPage
// ─────────────────────────────────────────────────────────────────────────────
export class ResultsPage {
  constructor (page) {
    this.page = page
  }

  async waitForHeader ({ timeout = 60_000 } = {}) {
    await this.page.locator(SEL.RESULT_HEADER).waitFor({ state: 'visible', timeout })
  }

  async selectResultType (typeCode) {
    await this.page.locator(SEL.RESULT_TYPE_SELECT).selectOption(typeCode)
    await this.page.waitForTimeout(600)
  }

  async selectResult (optionValue) {
    await this.page.locator(SEL.RESULT_ITEM_SELECT).selectOption(optionValue)
    await this.page.waitForTimeout(1000)
  }

  async getResultOptionCount () {
    return this.page.locator(`${SEL.RESULT_ITEM_SELECT} option`).count()
  }

  async setImportMode (mode) {
    await this.page.locator(SEL.RESULT_IMPORT_MODE_SELECT).selectOption(mode)
    await this.page.waitForTimeout(200)
  }

  async setImportStrict (strict) {
    const checkbox = this.page.locator(SEL.RESULT_IMPORT_STRICT_CHECKBOX).first()
    await checkbox.setChecked(!!strict)
    await this.page.waitForTimeout(150)
  }

  async importBundleObject (bundleObject) {
    const payload = Buffer.from(JSON.stringify(bundleObject, null, 2), 'utf-8')
    await this.page.setInputFiles(SEL.RESULT_IMPORT_FILE_INPUT, {
      name: 'ijt-results-import.json',
      mimeType: 'application/json',
      buffer: payload
    })
  }

  async importBundleObjectViaFileChooser (bundleObject, filename = 'ijt-results-import.json') {
    const payload = Buffer.from(JSON.stringify(bundleObject, null, 2), 'utf-8')
    const fileChooserPromise = this.page.waitForEvent('filechooser')
    await this.page.locator(SEL.RESULT_IMPORT_BUTTON).first().click()
    const fileChooser = await fileChooserPromise
    await fileChooser.setFiles({
      name: filename,
      mimeType: 'application/json',
      buffer: payload
    })
  }

  async exportCurrentResults () {
    const downloadPromise = this.page.waitForEvent('download')
    await this.page.locator(SEL.RESULT_EXPORT_BUTTON).first().click()
    return downloadPromise
  }

  async getStatusText () {
    const status = this.page.locator(SEL.RESULT_STATUS).first()
    return (await status.textContent())?.trim() || ''
  }

  async waitForResultBox ({ timeout = 60_000 } = {}) {
    await this.page.locator(SEL.COMPLE_WRAPPER).first().waitFor({ state: 'visible', timeout })
  }

  async countResultNodes (selector) {
    return this.page.locator(selector).count()
  }

  /** Select the "Latest" from any result type and verify the tree rendered. */
  async viewLatestOfType (typeCode) {
    await this.selectResultType(typeCode)
    const count = await this.getResultOptionCount()
    if (count < 2) return false   // only "Unresolved" placeholder
    await this.selectResult('-1')
    return true
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// JointDemoPage
// ─────────────────────────────────────────────────────────────────────────────
export class JointDemoPage {
  constructor (page) {
    this.page = page
  }

  async waitForButtons ({ timeout = 60_000 } = {}) {
    await this.page.locator(SEL.DEMO_SELECT_JOINT1).first().waitFor({ state: 'visible', timeout })
  }

  async waitForResolvedProductUri ({ timeout = 60_000 } = {}) {
    await this.page.locator(SEL.DEMO_ACTIVE_URI).first().waitFor({ state: 'visible', timeout })
    await this.page.waitForFunction(
      (selector) => {
        const text = document.querySelector(selector)?.textContent || ''
        return text.includes('Active ProductInstanceUri:') &&
          (text.includes('(auto-detected)') || text.includes('(selected from server)') || text.includes('(from Settings)'))
      },
      SEL.DEMO_ACTIVE_URI,
      { timeout }
    )
  }

  async selectJoint1 () {
    await this.waitForResolvedProductUri()
    await this.page.locator(SEL.DEMO_SELECT_JOINT1).first().click()
    await this.page.waitForTimeout(300)
  }

  async selectJoint2 () {
    await this.waitForResolvedProductUri()
    await this.page.locator(SEL.DEMO_SELECT_JOINT2).first().click()
    await this.page.waitForTimeout(300)
  }

  async simulateTightening () {
    await this.waitForResolvedProductUri()
    await this.page.locator(SEL.DEMO_SIMULATE_TIGHTEN).first().click()
    await this.page.waitForTimeout(800)
  }

  /** Full demo cycle: primary joint -> tighten -> secondary joint -> tighten */
  async runFullDemoCycle () {
    await this.selectJoint1()
    await this.simulateTightening()
    await this.selectJoint2()
    await this.simulateTightening()
    await this.page.waitForTimeout(3_000)  // allow results to propagate
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// OkRatePage
// ─────────────────────────────────────────────────────────────────────────────
export class OkRatePage {
  constructor (page) {
    this.page = page
  }

  async waitForView ({ timeout = 30_000 } = {}) {
    await this.page.locator(SEL.OK_RATE_VIEW).waitFor({ state: 'visible', timeout })
  }

  /** Returns the displayed OK-rate percentage string (e.g. "87.50%"). */
  async getOkRateText () {
    return this.page.locator(SEL.OK_RATE_VALUE).textContent()
  }

  async simulateOk () {
    await this.page.locator(SEL.OK_RATE_SIMULATE_OK).first().click()
    await this.page.waitForTimeout(600)
  }

  async simulateNok () {
    await this.page.locator(SEL.OK_RATE_SIMULATE_NOK).first().click()
    await this.page.waitForTimeout(600)
  }

  async clearCounters () {
    await this.page.locator(SEL.OK_RATE_CLEAR).first().click()
    await this.page.waitForTimeout(300)
  }

  /** Parse the percentage value from the displayed text. Returns NaN if unparseable. */
  async getOkRateNumber () {
    const text = (await this.getOkRateText()) ?? ''
    return parseFloat(text.replace('%', '').trim())
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// AddressSpacePage
// ─────────────────────────────────────────────────────────────────────────────
export class AddressSpacePage {
  constructor (page) {
    this.page = page
  }

  async waitForTree ({ timeout = 30_000 } = {}) {
    await this.page.locator(SEL.TREE_BUTTON).first().waitFor({ state: 'visible', timeout })
  }

  /** Returns number of visible tree-node buttons. */
  async getVisibleNodeCount () {
    return this.page.locator(SEL.TREE_BUTTON).count()
  }

  treeButtonByBrowseName (name) {
    return this.page.locator(SEL.TREE_BUTTON_BY_BROWSE_NAME(name)).first()
  }

  async waitForBrowseName (name, { timeout = 15_000 } = {}) {
    const btn = this.treeButtonByBrowseName(name)
    await btn.waitFor({ state: 'visible', timeout })
    return btn
  }

  async hasBrowseName (name) {
    return (await this.page.locator(SEL.TREE_BUTTON_BY_BROWSE_NAME(name)).count()) > 0
  }

  async isBrowseNameOpen (name) {
    const btn = await this.waitForBrowseName(name)
    return btn.evaluate((button) => button.parentElement?.classList.contains('is-open') ?? false)
  }

  async expandBrowseName (name, { expectedChild, timeout = 15_000 } = {}) {
    const btn = await this.waitForBrowseName(name, { timeout })
    const isOpen = await btn.evaluate((button) => button.parentElement?.classList.contains('is-open') ?? false)
    if (!isOpen) {
      await btn.click()
    }

    if (expectedChild) {
      await this.waitForBrowseName(expectedChild, { timeout })
      return
    }

    await this.page.waitForFunction(
      (selector) => {
        const button = document.querySelector(selector)
        return !!button?.parentElement?.classList.contains('is-open')
      },
      SEL.TREE_BUTTON_BY_BROWSE_NAME(name),
      { timeout }
    )
  }

  async collapseBrowseName (name, { timeout = 15_000 } = {}) {
    const btn = await this.waitForBrowseName(name, { timeout })
    const isOpen = await btn.evaluate((button) => button.parentElement?.classList.contains('is-open') ?? false)
    if (isOpen) {
      await btn.click()
    }
    await this.page.waitForFunction(
      (selector) => {
        const button = document.querySelector(selector)
        return !!button && !button.parentElement?.classList.contains('is-open')
      },
      SEL.TREE_BUTTON_BY_BROWSE_NAME(name),
      { timeout }
    )
  }

  async expandByBrowseName (path, { expectedChild, timeout = 15_000 } = {}) {
    for (let i = 0; i < path.length; i++) {
      const current = path[i]
      const childToWaitFor = path[i + 1] ?? (i === path.length - 1 ? expectedChild : undefined)
      await this.expandBrowseName(current, { expectedChild: childToWaitFor, timeout })
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// ServersPage
// ─────────────────────────────────────────────────────────────────────────────
export class ServersPage {
  constructor (page) {
    this.page = page
  }

  async waitForServerList ({ timeout = 30_000 } = {}) {
    await this.page.locator(SEL.SERVER_ROWS).waitFor({ state: 'visible', timeout })
  }

  async getServerRowCount () {
    return this.page.locator(`${SEL.SERVER_ROWS} ${SEL.SERVER_ROW}`).count()
  }

  async hasServerName (name) {
    const rows = this.page.locator(SEL.SERVER_ROWS)
    await rows.waitFor({ state: 'visible' })
    return rows.locator('input').evaluateAll(
      (inputs, expected) => inputs.some((input) => input.value === expected),
      name
    )
  }

  async clickAddServer () {
    await this.page.locator(SEL.SERVER_ADD_BTN).first().click()
    await this.page.waitForTimeout(300)
  }

  async clickSave () {
    const btn = this.page.locator(SEL.SERVER_SAVE_BTN)
    if ((await btn.count()) > 0) {
      await btn.first().click()
      await this.page.waitForTimeout(300)
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// AssetsPage
// ─────────────────────────────────────────────────────────────────────────────
export class AssetsPage {
  constructor (page) {
    this.page = page
  }

  async waitForAssets ({ timeout = 60_000 } = {}) {
    await this.page.locator(SEL.ASSET_BOX).waitFor({ state: 'visible', timeout })
  }

  async hasAssetContent () {
    const box = this.page.locator(SEL.ASSET_BOX)
    const text = (await box.textContent()) ?? ''
    return text.trim().length > 0
  }
}
