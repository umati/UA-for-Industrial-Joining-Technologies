import { describe, it, expect } from 'vitest'
import { readFile, access } from 'node:fs/promises'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const projectRoot = join(__dirname, '..', '..', '..')

describe('repo-hygiene', () => {
  it('package.json exists and has correct name field', async () => {
    const content = await readFile(join(projectRoot, 'package.json'), 'utf-8')
    const pkg = JSON.parse(content)
    expect(pkg.name).toBeDefined()
    expect(typeof pkg.name).toBe('string')
    expect(pkg.name.length).toBeGreaterThan(0)
  })

  it('package.json has test script defined', async () => {
    const content = await readFile(join(projectRoot, 'package.json'), 'utf-8')
    const pkg = JSON.parse(content)
    expect(pkg.scripts).toBeDefined()
    expect(pkg.scripts.test).toBeDefined()
  })

  it('package.json has test:unit:js script', async () => {
    const content = await readFile(join(projectRoot, 'package.json'), 'utf-8')
    const pkg = JSON.parse(content)
    expect(pkg.scripts['test:unit:js']).toBeDefined()
  })

  it('README.md exists and is non-empty', async () => {
    const content = await readFile(join(projectRoot, 'README.md'), 'utf-8')
    expect(content.trim().length).toBeGreaterThan(50)
  })

  it('eslint.config.js exists', async () => {
    await expect(access(join(projectRoot, 'eslint.config.js'))).resolves.toBeUndefined()
  })

  it('vitest.config.mjs exists', async () => {
    await expect(access(join(projectRoot, 'vitest.config.mjs'))).resolves.toBeUndefined()
  })

  it('package.json has no local path dependencies', async () => {
    const content = await readFile(join(projectRoot, 'package.json'), 'utf-8')
    const pkg = JSON.parse(content)
    const allDeps = { ...pkg.dependencies, ...pkg.devDependencies }
    const localDeps = Object.entries(allDeps).filter(([, v]) => v.startsWith('file:') || v.startsWith('./') || v.startsWith('../'))
    expect(localDeps).toEqual([])
  })

  it('package.json type is "module"', async () => {
    const content = await readFile(join(projectRoot, 'package.json'), 'utf-8')
    const pkg = JSON.parse(content)
    expect(pkg.type).toBe('module')
  })
})

// ---------------------------------------------------------------------------
// Security regression tests — innerHTML XSS prevention
// ---------------------------------------------------------------------------

describe('security — no innerHTML with variable data', () => {
  it('connection-graphics.mjs uses textContent not innerHTML for ESTABLISHED/LOST labels', async () => {
    const src = await readFile(
      join(projectRoot, 'javascripts', 'views', 'connection', 'connection-graphics.mjs'),
      'utf-8'
    )
    // innerHTML assignments with these literal strings must be gone
    expect(src).not.toContain("innerHTML = 'ESTABLISHED'")
    expect(src).not.toContain('innerHTML = "ESTABLISHED"')
    expect(src).not.toContain("innerHTML = 'LOST'")
    expect(src).not.toContain('innerHTML = "LOST"')
    // textContent replacements must be present
    expect(src).toContain("textContent = 'ESTABLISHED'")
    expect(src).toContain("textContent = 'LOST'")
  })
})

// ---------------------------------------------------------------------------
// Security regression tests — unhandled promise rejections
// ---------------------------------------------------------------------------

describe('security — promise error handling', () => {
  it('address-space.mjs initiate() propagates errors with .catch()', async () => {
    const src = await readFile(
      join(projectRoot, 'javascripts', 'ijt-support', 'address-space', 'address-space.mjs'),
      'utf-8'
    )
    // The initiate() method must have a .catch() so rejected promises surface as errors
    // (without it, unhandled rejections are silently swallowed)
    expect(src).toContain('.catch(')
  })

  it('method-manager.mjs promise chains have .catch(reject) error propagation', async () => {
    const src = await readFile(
      join(projectRoot, 'javascripts', 'ijt-support', 'methods', 'method-manager.mjs'),
      'utf-8'
    )
    expect(src).toContain('.catch(reject)')
  })
})

