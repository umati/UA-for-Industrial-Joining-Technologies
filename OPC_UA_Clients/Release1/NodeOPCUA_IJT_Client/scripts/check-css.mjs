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
const quotedColorProperties = new Set(['background', 'background-color', 'color'])

function stripBlockComments (line, inBlockComment) {
  let cursor = 0
  let output = ''
  let commentState = inBlockComment

  while (cursor < line.length) {
    if (commentState) {
      const endIdx = line.indexOf('*/', cursor)
      if (endIdx === -1) {
        return { text: output, inBlockComment: true }
      }
      cursor = endIdx + 2
      commentState = false
      continue
    }

    const startIdx = line.indexOf('/*', cursor)
    if (startIdx === -1) {
      output += line.slice(cursor)
      break
    }

    output += line.slice(cursor, startIdx)
    cursor = startIdx + 2
    commentState = true
  }

  return { text: output, inBlockComment: commentState }
}

function parseDeclaration (line) {
  const match = line.match(/^\s*([a-z][a-z0-9-]*)\s*:\s*(.*?)\s*(;?)\s*$/i)
  if (!match) return null

  const property = match[1].toLowerCase()
  const value = match[2].trim()
  const hasSemicolon = match[3] === ';'

  return { property, value, hasSemicolon }
}

function checkFile (filePath) {
  const content = fs.readFileSync(filePath, 'utf8')
  const lines = content.split(/\r?\n/)

  let inBlockComment = false

  lines.forEach((line, idx) => {
    const lineNo = idx + 1
    const withoutComments = stripBlockComments(line, inBlockComment)
    inBlockComment = withoutComments.inBlockComment
    const code = withoutComments.text
    const trimmed = code.trim()

    if (trimmed.startsWith('//') || trimmed === '') return

    if (/^\s*;\s*$/.test(line)) {
      findings.push(`${filePath}:${lineNo} standalone semicolon`)
    }

    if (/[ \t]+$/.test(line)) {
      findings.push(`${filePath}:${lineNo} trailing whitespace`)
    }

    const declaration = parseDeclaration(code)
    if (!declaration) return

    if (/:\S/.test(code)) {
      findings.push(`${filePath}:${lineNo} missing space after colon`)
    }

    if (declaration.property === 'border-radius' && /^\d+(\.\d+)?$/.test(declaration.value)) {
      findings.push(`${filePath}:${lineNo} border-radius missing unit`)
    }

    if (quotedColorProperties.has(declaration.property) && /^['"][^'"]+['"]$/.test(declaration.value)) {
      findings.push(`${filePath}:${lineNo} quoted color value`)
    }

    if (!declaration.hasSemicolon) {
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
