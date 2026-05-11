import { test, expect } from '../e2e/e2e-fixtures.mjs'
import { makeResultBundle } from './result-bundle-fixture.mjs'

test('edge-result-import-filechooser-smoke', async ({ connected: app }) => {
  test.setTimeout(120_000)

  const results = await app.openResults()
  await results.waitForHeader({ timeout: 60_000 })

  const resultId = `compatibility-smoke-import-${Date.now()}`
  const bundle = makeResultBundle(resultId)

  await results.setImportMode('skip-duplicates')
  await results.setImportStrict(false)
  await results.importBundleObjectViaFileChooser(bundle, 'ijt-compatibility-smoke-import.json')

  await expect.poll(async () => results.getStatusText(), { timeout: 10_000 }).toContain('Imported 1')

  await results.importBundleObjectViaFileChooser(bundle, 'ijt-compatibility-smoke-import.json')
  await expect.poll(async () => results.getStatusText(), { timeout: 10_000 }).toContain('duplicate_result_id:1')
})
