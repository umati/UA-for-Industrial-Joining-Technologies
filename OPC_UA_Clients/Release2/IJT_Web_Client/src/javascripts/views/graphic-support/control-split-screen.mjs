import BasicScreen from './basic-screen.mjs'
/**
 * Support class that creates the split screen
 * Use this.controlArea to add things to interact with
 * Use this.messageDisplay(msg) to desplay user feedback
 * Implement your own initiate() function to run code every time the tab is opened
 */
export default class ControlSplitScreen extends BasicScreen {
  constructor (title, leftText, rightText) {
    super(title)

    this.columnSetter = document.createElement('div')
    this.columnSetter.classList.add('columns')
    this.backGround.appendChild(this.columnSetter)

    this.controlArea = this.makeNamedArea(leftText, 'lefthalf', this.columnSetter)

    this.controls = document.createElement('div')
    this.controls.classList.add('doublecolumnleft')
    this.controlArea.appendChild(this.controls)

    this.viewArea = this.makeNamedArea(rightText, 'righthalf', this.columnSetter)

    this.views = document.createElement('div')
    this.views.classList.add('doublecolumnright')
    this.viewArea.appendChild(this.views)

    this.setupColumnResizer()
  }

  setupColumnResizer () {
    if (!this.columnSetter || !this.controlArea?.parentArea || !this.viewArea?.parentArea) {
      return
    }

    const leftPanel = this.controlArea.parentArea
    const rightPanel = this.viewArea.parentArea
    const storageKey = this.makeSplitStorageKey()
    const minPaneWidth = 220
    let lastLeftWidth = null
    let dragging = false
    let startX = 0
    let startLeftWidth = 0

    const handle = document.createElement('div')
    handle.classList.add('columnResizeHandle')
    handle.setAttribute('role', 'separator')
    handle.setAttribute('aria-orientation', 'vertical')
    handle.title = 'Drag to resize columns'

    const readStoredWidth = () => {
      try {
        const raw = window.localStorage.getItem(storageKey)
        const parsed = Number.parseFloat(raw)
        return Number.isFinite(parsed) ? parsed : null
      } catch {
        return null
      }
    }

    const persistWidth = (value) => {
      if (!Number.isFinite(value)) {
        return
      }
      try {
        window.localStorage.setItem(storageKey, String(Math.round(value)))
      } catch {}
    }

    const getGap = () => {
      const styles = window.getComputedStyle(this.columnSetter)
      const rawGap = styles.columnGap || styles.gap || '0'
      const parsed = Number.parseFloat(rawGap)
      return Number.isFinite(parsed) ? parsed : 0
    }

    const isStackedLayout = () => {
      const direction = window.getComputedStyle(this.columnSetter).flexDirection || ''
      return direction.includes('column')
    }

    const updateHandlePosition = (leftWidth) => {
      const gap = getGap()
      handle.style.left = `${Math.round(leftWidth + (gap / 2))}px`
    }

    const clearSplitWidths = () => {
      leftPanel.style.width = ''
      rightPanel.style.width = ''
      handle.classList.add('is-hidden')
    }

    const setLeftWidth = (requestedWidth, { persist = false } = {}) => {
      const containerWidth = Math.max(1, this.columnSetter.getBoundingClientRect().width)
      if (containerWidth <= 1 || isStackedLayout()) {
        clearSplitWidths()
        return null
      }

      const gap = getGap()
      const availableWidth = Math.max(1, containerWidth - gap)
      const maxLeft = Math.max(minPaneWidth, availableWidth - minPaneWidth)
      const clampedLeft = Math.max(minPaneWidth, Math.min(maxLeft, requestedWidth))
      const rightWidth = Math.max(minPaneWidth, availableWidth - clampedLeft)

      leftPanel.style.width = `${clampedLeft}px`
      rightPanel.style.width = `${rightWidth}px`
      handle.classList.remove('is-hidden')
      updateHandlePosition(clampedLeft)
      lastLeftWidth = clampedLeft

      if (persist) {
        persistWidth(clampedLeft)
      }
      return clampedLeft
    }

    const refreshLayout = () => {
      if (isStackedLayout()) {
        clearSplitWidths()
        return
      }
      if (Number.isFinite(lastLeftWidth) && lastLeftWidth > 0) {
        setLeftWidth(lastLeftWidth)
        return
      }
      const stored = readStoredWidth()
      if (Number.isFinite(stored) && stored > 0) {
        setLeftWidth(stored)
        return
      }
      const measured = leftPanel.getBoundingClientRect().width
      if (Number.isFinite(measured) && measured > 0) {
        setLeftWidth(measured)
      }
    }

    const onPointerMove = (evt) => {
      if (!dragging) {
        return
      }
      const deltaX = evt.clientX - startX
      setLeftWidth(startLeftWidth + deltaX)
      evt.preventDefault()
    }

    const stopDragging = (evt) => {
      if (!dragging) {
        return
      }
      dragging = false
      handle.classList.remove('is-dragging')
      if (Number.isFinite(lastLeftWidth) && lastLeftWidth > 0) {
        persistWidth(lastLeftWidth)
      }
      try {
        handle.releasePointerCapture(evt.pointerId)
      } catch {}
      window.removeEventListener('pointermove', onPointerMove)
      window.removeEventListener('pointerup', stopDragging)
      window.removeEventListener('pointercancel', stopDragging)
    }

    const onPointerDown = (evt) => {
      if (isStackedLayout()) {
        return
      }
      evt.preventDefault()
      dragging = true
      handle.classList.add('is-dragging')
      startX = evt.clientX
      startLeftWidth = Number.isFinite(lastLeftWidth) && lastLeftWidth > 0
        ? lastLeftWidth
        : leftPanel.getBoundingClientRect().width
      try {
        handle.setPointerCapture(evt.pointerId)
      } catch {}
      window.addEventListener('pointermove', onPointerMove)
      window.addEventListener('pointerup', stopDragging)
      window.addEventListener('pointercancel', stopDragging)
    }

    this.columnSetter.classList.add('hasColumnResizer')
    this.columnSetter.appendChild(handle)
    handle.addEventListener('pointerdown', onPointerDown)
    window.addEventListener('resize', refreshLayout)

    if (typeof window.ResizeObserver === 'function') {
      this._splitResizeObserver = new window.ResizeObserver(() => {
        refreshLayout()
      })
      this._splitResizeObserver.observe(this.columnSetter)
    }

    window.requestAnimationFrame(() => {
      refreshLayout()
    })
  }

  makeSplitStorageKey () {
    const normalizedTitle = String(this.title || 'split-screen')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
    return `ijt.split-screen.left-width.${normalizedTitle || 'default'}`
  }
}
