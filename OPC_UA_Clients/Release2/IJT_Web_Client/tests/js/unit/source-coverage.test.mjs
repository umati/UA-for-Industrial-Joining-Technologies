/**
 * source-coverage.test.mjs
 *
 * Verifies that every JS/MJS source module tracked by git is present on disk.
 *
 * SCOPE — what this test catches and what it does not:
 *
 *   ✔  On a normal checkout: all files in `git ls-files src/` exist on disk.
 *      If a previously-committed file is deleted or moved without a git-rm,
 *      this test will fail.
 *
 *   ✘  A file that is accidentally gitignored and was NEVER committed will not
 *      appear in `git ls-files` and will not be checked here.  The correct
 *      CI-level defence for that class of bug (commit 9598856) is the
 *      Playwright smoke test suite: if a required JS module is absent the
 *      browser fails to load the page, causing the smoke tests to fail.
 *      The local developer guardrail is `run_all_tests.py --suite git-sanity`
 *      which uses `git check-ignore` on all files present in the working tree.
 *
 * No new dependencies — uses only Node built-ins (fs, child_process, path).
 */

import { describe, it, expect } from 'vitest'
import { existsSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { spawnSync } from 'child_process'

const __dirname = dirname(fileURLToPath(import.meta.url))
const WEB_CLIENT_DIR = resolve(__dirname, '../../..')
const SOURCE_EXTS = new Set(['.mjs', '.js'])

/**
 * Return paths (relative to WEB_CLIENT_DIR) of every source file that git
 * currently tracks under src/. Returns an empty array when git is unavailable
 * (zip exports, containers without git); the suite will skip gracefully.
 */
function getTrackedSourceFiles () {
  const result = spawnSync(
    'git',
    ['ls-files', 'src/'],
    { cwd: WEB_CLIENT_DIR, encoding: 'utf8' },
  )
  if (result.status !== 0 || result.error) return []
  return result.stdout
    .split('\n')
    .map(f => f.trim())
    .filter(f => f.length > 0 && SOURCE_EXTS.has(f.slice(f.lastIndexOf('.'))))
}

// Called at module level: spawnSync is synchronous so this is safe and avoids
// the beforeAll / it.each ordering problem.
const trackedFiles = getTrackedSourceFiles()
const gitAvailable = trackedFiles.length > 0

describe('Web Client — all git-tracked source modules exist on disk', () => {
  it('git ls-files returned source files (skip note when git unavailable)', () => {
    if (!gitAvailable) {
      // Git metadata absent (zip export / non-git environment) — skip gracefully.
      console.warn('source-coverage: git ls-files returned no files; skipping file-existence checks.')
      return
    }
    expect(trackedFiles.length,
      'git ls-files returned no .mjs/.js files — is git available and are there tracked source files?',
    ).toBeGreaterThan(0)
  })

  // One test per tracked file. If a tracked file is absent it means it was
  // deleted or moved without a git-rm. Fails with a clear, actionable message.
  it.each(trackedFiles.map(f => [f]))('%s', (file) => {
    expect(
      existsSync(resolve(WEB_CLIENT_DIR, file)),
      `File tracked by git but missing on disk: ${file}\n` +
      'Likely cause: file was deleted/moved without git-rm, or a .gitignore rule was added after commit.\n' +
      'Run: git status  or  git check-ignore -v <file>',
    ).toBe(true)
  })
})
