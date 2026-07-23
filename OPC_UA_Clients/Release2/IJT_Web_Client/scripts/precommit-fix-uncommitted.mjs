import { execFileSync, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, join } from 'node:path'

const require = createRequire(import.meta.url)

function unique (values) {
  return [...new Set(values)]
}

function getChangedTrackedFiles () {
  const output = execFileSync('git', ['status', '--porcelain'], { encoding: 'utf8' })
  const lines = output
    .split(/\r?\n/u)
    .map((line) => line.trim())
    .filter(Boolean)
  const files = []
  for (const line of lines) {
    const status = line.slice(0, 2)
    if (status === '??' || status.includes('D')) {
      continue
    }
    const rawPath = line.slice(3).trim()
    if (!rawPath) {
      continue
    }
    const renamedSeparator = ' -> '
    const path = rawPath.includes(renamedSeparator)
      ? rawPath.split(renamedSeparator).at(-1)
      : rawPath
    if (path) {
      files.push(path)
    }
  }
  return unique(files).filter((file) => existsSync(file))
}

function runNodeTool (toolPath, args) {
  const result = spawnSync(process.execPath, [toolPath, ...args], { stdio: 'inherit' })
  if (result.status !== 0) {
    process.exit(result.status || 1)
  }
}

const changedTrackedFiles = getChangedTrackedFiles()
const jsFiles = changedTrackedFiles.filter((file) => file.endsWith('.js') || file.endsWith('.mjs'))
const cssFiles = changedTrackedFiles.filter((file) => file.endsWith('.css'))
const lintTargets = unique([...jsFiles, ...cssFiles])

if (lintTargets.length === 0) {
  process.exit(0)
}

if (jsFiles.length > 0) {
  const eslintRoot = dirname(require.resolve('eslint/package.json'))
  const eslintBin = join(eslintRoot, 'bin', 'eslint.js')
  runNodeTool(eslintBin, ['--fix', '--config', 'eslint.config.mjs', ...jsFiles])
}

if (cssFiles.length > 0) {
  const stylelintRoot = dirname(require.resolve('stylelint/package.json'))
  const stylelintBin = join(stylelintRoot, 'bin', 'stylelint.mjs')
  runNodeTool(stylelintBin, ['--fix', ...cssFiles])
}

if (process.env.PRECOMMIT_AUTO_STAGE === '1') {
  execFileSync('git', ['add', '--', ...lintTargets], { stdio: 'inherit' })
}
