export function attachChildOutput (child, { stdout = true, stderr = true } = {}) {
  if (stdout && child.stdout) {
    child.stdout.on('data', (chunk) => {
      process.stdout.write(chunk)
    })
  }
  if (stderr && child.stderr) {
    child.stderr.on('data', (chunk) => {
      process.stderr.write(chunk)
    })
  }
}

export function waitForServerReady (child, timeoutMs = 15000, marker = 'Socket.IO server running at') {
  return new Promise((resolve, reject) => {
    let settled = false
    const settle = (fn, value) => {
      if (settled) {
        return
      }
      settled = true
      clearTimeout(timeout)
      if (child.stdout) {
        child.stdout.off('data', onStdout)
      }
      child.off('error', onError)
      child.off('exit', onExit)
      fn(value)
    }

    const onStdout = (chunk) => {
      const text = chunk.toString()
      if (text.includes(marker)) {
        settle(resolve)
      }
    }
    const onError = (error) => {
      settle(reject, error)
    }
    const onExit = (code) => {
      settle(reject, new Error(`Server exited early with code ${code ?? 'null'}`))
    }

    const timeout = setTimeout(() => {
      settle(reject, new Error('Timed out waiting for server startup log line'))
    }, timeoutMs)

    if (child.stdout) {
      child.stdout.on('data', onStdout)
    }
    child.on('error', onError)
    child.on('exit', onExit)
  })
}
