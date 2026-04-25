import { test as base } from 'playwright/test'

const BASE_URL = 'http://localhost:3000'
const OPCUA_ENDPOINT = 'opc.tcp://localhost:40451'

async function isServerRunning () {
  try {
    const res = await fetch(BASE_URL)
    return res.ok
  } catch {
    return false
  }
}

export const test = base.extend({
  page: async ({ page }, use) => {
    if (!await isServerRunning()) {
      test.skip(true, 'IJT Node Client not running — start with: node index.js')
    }
    await use(page)
  }
})

export { BASE_URL, OPCUA_ENDPOINT }
export { expect } from 'playwright/test'
