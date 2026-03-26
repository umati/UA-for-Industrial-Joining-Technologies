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
