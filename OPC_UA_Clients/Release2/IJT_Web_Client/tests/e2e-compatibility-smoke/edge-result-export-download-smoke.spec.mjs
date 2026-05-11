import { promises as fs } from 'node:fs'

import { test, expect } from '../e2e/e2e-fixtures.mjs'
import { makeResultBundle } from './result-bundle-fixture.mjs'

test('edge-result-export-download-smoke', async ({ connected: app }) => {
  test.setTimeout(120_000)

  const results = await app.openResults()
  await results.waitForHeader({ timeout: 60_000 })

  const resultId = `compatibility-smoke-export-${Date.now()}`
  const bundle = makeResultBundle(resultId)

  await results.setImportMode('replace')
  await results.setImportStrict(false)
  await results.importBundleObject(bundle)
  await expect.poll(async () => results.getStatusText(), { timeout: 10_000 }).toContain('Imported 1')

  const download = await results.exportCurrentResults()
  expect(download.suggestedFilename()).toMatch(/^ijt-results-.+\.json$/)

  const downloadPath = await download.path()
  expect(downloadPath).toBeTruthy()
  const exported = JSON.parse(await fs.readFile(downloadPath, 'utf-8'))

  expect(exported.type).toBe('ijt-result-export')
  expect(exported.results.some((result) => result.ResultMetaData?.ResultId === resultId)).toBe(true)
})
