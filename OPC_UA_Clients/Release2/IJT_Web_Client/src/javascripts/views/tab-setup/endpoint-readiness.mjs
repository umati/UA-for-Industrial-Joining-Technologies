export const READINESS_STATES = Object.freeze({
  CONNECTING: 'connecting',
  READY: 'ready',
  LIMITED: 'limited',
  DISCONNECTED: 'disconnected'
})

const STATE_LABELS = Object.freeze({
  [READINESS_STATES.CONNECTING]: 'Connecting',
  [READINESS_STATES.READY]: 'Ready',
  [READINESS_STATES.LIMITED]: 'Limited',
  [READINESS_STATES.DISCONNECTED]: 'Disconnected'
})

const STATE_DESCRIPTIONS = Object.freeze({
  [READINESS_STATES.CONNECTING]: 'Connecting to the endpoint and preparing IJT data.',
  [READINESS_STATES.READY]: 'Endpoint is ready: connected, subscribed, and IJT Tightening System discovered.',
  [READINESS_STATES.LIMITED]: 'Endpoint is connected, but one or more IJT readiness checks are incomplete.',
  [READINESS_STATES.DISCONNECTED]: 'Endpoint is disconnected.'
})

const CHECK_LABELS = Object.freeze({
  connection: 'Connection',
  subscription: 'Subscription',
  tighteningSystem: 'IJT Tightening System'
})

function setClass (element, className, enabled) {
  if (enabled) {
    element.classList.add(className)
  } else {
    element.classList.remove(className)
  }
}

export function endpointReadinessFromChecks (checks) {
  if (checks.closing || (!checks.connection && !checks.attemptConnection)) {
    return READINESS_STATES.DISCONNECTED
  }
  if (!checks.connection) {
    return READINESS_STATES.CONNECTING
  }
  if (checks.subscription && checks.tighteningSystem) {
    return READINESS_STATES.READY
  }
  return READINESS_STATES.LIMITED
}

function formatCheckValue (ready, pendingLabel = 'Pending') {
  return ready ? 'OK' : pendingLabel
}

function appendDiagnosticRow (doc, list, label, value) {
  const term = doc.createElement('dt')
  term.textContent = label
  const description = doc.createElement('dd')
  description.textContent = value
  list.appendChild(term)
  list.appendChild(description)
  return description
}

export function createEndpointReadiness ({ connectionManager, endpointUrl, documentRef = document }) {
  const states = {
    attemptConnection: Boolean(connectionManager?.attemptconnection),
    connection: Boolean(connectionManager?.connection),
    subscription: Boolean(connectionManager?.subscription),
    tighteningSystem: Boolean(connectionManager?.tighteningsystem),
    closing: Boolean(connectionManager?.attemptclose)
  }

  const root = documentRef.createElement('div')
  root.classList.add('endpointHeader')

  const endpointLabel = documentRef.createElement('span')
  endpointLabel.classList.add('endpointHeaderUrl')
  endpointLabel.textContent = endpointUrl || ''
  root.appendChild(endpointLabel)

  const details = documentRef.createElement('details')
  details.classList.add('endpointReadinessDetails')
  root.appendChild(details)

  const summary = documentRef.createElement('summary')
  summary.classList.add('endpointReadinessSummary')
  details.appendChild(summary)

  const pill = documentRef.createElement('span')
  pill.classList.add('endpointReadinessPill')
  summary.appendChild(pill)

  const panel = documentRef.createElement('div')
  panel.classList.add('endpointReadinessPanel')
  details.appendChild(panel)

  const title = documentRef.createElement('div')
  title.classList.add('endpointReadinessPanelTitle')
  title.textContent = 'Readiness diagnostics'
  panel.appendChild(title)

  const list = documentRef.createElement('dl')
  list.classList.add('endpointReadinessChecks')
  panel.appendChild(list)

  const checkValues = {
    connection: appendDiagnosticRow(documentRef, list, CHECK_LABELS.connection, 'Pending'),
    subscription: appendDiagnosticRow(documentRef, list, CHECK_LABELS.subscription, 'Pending'),
    tighteningSystem: appendDiagnosticRow(documentRef, list, CHECK_LABELS.tighteningSystem, 'Pending')
  }

  function render () {
    const readiness = endpointReadinessFromChecks(states)
    root.setAttribute('data-endpoint-readiness-state', readiness)
    pill.textContent = STATE_LABELS[readiness]
    pill.title = STATE_DESCRIPTIONS[readiness]
    pill.setAttribute('aria-label', `${STATE_LABELS[readiness]} endpoint status`)
    for (const state of Object.values(READINESS_STATES)) {
      setClass(pill, `endpointReadinessPill--${state}`, readiness === state)
    }

    checkValues.connection.textContent = formatCheckValue(
      states.connection,
      states.attemptConnection ? 'Connecting' : 'Disconnected'
    )
    checkValues.subscription.textContent = formatCheckValue(states.subscription)
    checkValues.tighteningSystem.textContent = formatCheckValue(states.tighteningSystem)
  }

  const statesMap = connectionManager?.CONNECTION_STATES || {}
  const subscriptions = [
    [statesMap.ATTEMPT_CONNECTION, 'attemptConnection'],
    [statesMap.CONNECTION, 'connection'],
    [statesMap.SUBSCRIPTION, 'subscription'],
    [statesMap.TIGHTENING_SYSTEM, 'tighteningSystem'],
    [statesMap.ATTEMPT_CLOSE, 'closing']
  ]

  for (const [stateName, key] of subscriptions) {
    if (stateName && typeof connectionManager?.subscribe === 'function') {
      connectionManager.subscribe(stateName, (active) => {
        states[key] = Boolean(active)
        render()
      })
    }
  }

  render()
  return root
}
