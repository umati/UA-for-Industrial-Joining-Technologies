import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..')

const cssFiles = [
  path.join(projectRoot, 'nodeStyle.css')
]

const findings = []

function checkFile (filePath) {
  const content = fs.readFileSync(filePath, 'utf8')
  const lines = content.split(/\r?\n/)

  let inBlockComment = false

  lines.forEach((line, idx) => {
    const lineNo = idx + 1
    const trimmed = line.trim()

    // Track block comments to avoid false positives on commented declarations.
    if (inBlockComment) {
      if (trimmed.includes('*/')) inBlockComment = false
      return
    }
    if (trimmed.startsWith('/*')) {
      if (!trimmed.includes('*/')) inBlockComment = true
      return
    }
    if (trimmed.startsWith('//') || trimmed === '') return

    if (/^\s*;\s*$/.test(line)) {
      findings.push(`${filePath}:${lineNo} standalone semicolon`)
    }

    if (/[ \t]+$/.test(line)) {
      findings.push(`${filePath}:${lineNo} trailing whitespace`)
    }

    if (/^\s*[a-z-]+\s*:[^\s]/i.test(line)) {
      findings.push(`${filePath}:${lineNo} missing space after colon`)
    }

    if (/^\s*border-radius\s*:\s*\d+(\.\d+)?\s*;\s*$/i.test(line)) {
      findings.push(`${filePath}:${lineNo} border-radius missing unit`)
    }

    if (/^\s*(background|background-color|color)\s*:\s*['"][^'"]+['"]\s*;\s*$/i.test(line)) {
      findings.push(`${filePath}:${lineNo} quoted color value`)
    }

    const looksLikeDeclaration = /^\s*[a-z-]+\s*:[^;{}]+$/i.test(line)
    if (looksLikeDeclaration && !trimmed.endsWith(';')) {
      findings.push(`${filePath}:${lineNo} missing semicolon`)
    }
  })
}

for (const filePath of cssFiles) {
  if (!fs.existsSync(filePath)) {
    findings.push(`${filePath}:1 file not found`)
    continue
  }
  checkFile(filePath)
}

if (findings.length > 0) {
  console.error('CSS checks failed:')
  for (const finding of findings) {
    console.error(`- ${finding}`)
  }
  process.exit(1)
}

console.log('CSS checks passed')
