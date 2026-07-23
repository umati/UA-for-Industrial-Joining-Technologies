import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const packageRoot = dirname(dirname(fileURLToPath(import.meta.url)))
const huskyBin = join(packageRoot, 'node_modules', 'husky', 'bin.js')

function isProductionInstall () {
  const omit = process.env.npm_config_omit ?? ''
  return process.env.NODE_ENV === 'production' || omit.split(',').includes('dev')
}

function getGitRoot () {
  const result = spawnSync('git', ['-C', packageRoot, 'rev-parse', '--show-toplevel'], {
    encoding: 'utf8'
  })
  if (result.status !== 0) {
    return null
  }
  return result.stdout.trim()
}

if (isProductionInstall() || !existsSync(huskyBin)) {
  process.exit(0)
}

const gitRoot = getGitRoot()
if (!gitRoot) {
  process.exit(0)
}

const hooksPath = relative(gitRoot, join(packageRoot, '.husky')).replaceAll('\\', '/')
const result = spawnSync(process.execPath, [huskyBin, hooksPath], {
  cwd: gitRoot,
  stdio: 'inherit'
})

process.exit(result.status ?? 1)
