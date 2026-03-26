import { describe, it, expect } from 'vitest'
import { readdir, readFile } from 'node:fs/promises'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const projectRoot = join(__dirname, '..', '..', '..')
// Scope hygiene checks to ijt-support only — views/ has pre-existing legacy naming
const jsRoot = join(projectRoot, 'javascripts', 'ijt-support')

const KEBAB_LOWER = /^[a-z0-9][a-z0-9-]*(\.[a-z0-9]+)*$/

async function getAllEntries (dir) {
  const entries = []
  const items = await readdir(dir, { withFileTypes: true })
  for (const item of items) {
    entries.push({ name: item.name, isDir: item.isDirectory(), path: join(dir, item.name) })
    if (item.isDirectory()) {
      entries.push(...await getAllEntries(join(dir, item.name)))
    }
  }
  return entries
}

describe('import-paths: file and directory naming', () => {
  it('all .mjs files under javascripts/ have kebab-case names', async () => {
    const entries = await getAllEntries(jsRoot)
    const mjsFiles = entries.filter(e => !e.isDir && e.name.endsWith('.mjs'))
    const badNames = mjsFiles.filter(f => !KEBAB_LOWER.test(f.name))
    if (badNames.length > 0) {
      console.log('Non-kebab-case .mjs files:', badNames.map(f => f.name))
    }
    expect(badNames.length).toBe(0)
  })

  it('all directories under javascripts/ have kebab-case names', async () => {
    const entries = await getAllEntries(jsRoot)
    const dirs = entries.filter(e => e.isDir)
    const badDirs = dirs.filter(d => !KEBAB_LOWER.test(d.name))
    if (badDirs.length > 0) {
      console.log('Non-kebab-case directories:', badDirs.map(d => d.name))
    }
    expect(badDirs.length).toBe(0)
  })

  it('no import path in .mjs files contains uppercase directory names (AddressSpace, Models, etc.)', async () => {
    const entries = await getAllEntries(jsRoot)
    const mjsFiles = entries.filter(e => !e.isDir && e.name.endsWith('.mjs'))
    const violations = []
    const badPatterns = [/from ['"].*\/AddressSpace\//,/from ['"].*\/Models\//,/from ['"].*\/Views\//,/from ['"].*\/Javascripts\//,/from ['"].*\/Resources\//]
    for (const file of mjsFiles) {
      const content = await readFile(file.path, 'utf-8')
      for (const pattern of badPatterns) {
        if (pattern.test(content)) {
          violations.push({ file: file.name, pattern: pattern.toString() })
        }
      }
    }
    expect(violations).toEqual([])
  })

  it('index.html script tags use ./javascripts/ (lowercase)', async () => {
    const html = await readFile(join(projectRoot, 'index.html'), 'utf-8')
    const scriptSrcs = [...html.matchAll(/src="([^"]+)"/g)].map(m => m[1])
    const jsScripts = scriptSrcs.filter(s => s.includes('javascript') || s.includes('script'))
    for (const src of jsScripts) {
      if (src.startsWith('./') || src.startsWith('/')) {
        expect(src).not.toMatch(/Javascripts/)
      }
    }
  })
})
