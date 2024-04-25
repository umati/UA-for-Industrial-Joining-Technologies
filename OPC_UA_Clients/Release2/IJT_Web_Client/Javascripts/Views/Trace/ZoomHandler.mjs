export default class ZoomHandler {
  constructor (traceDisplay) {
    this.canvasCoverLayer = traceDisplay.canvasCoverLayer
    this.chartManager = traceDisplay.chartManager
  }

  zoomBoxDraw (pos1, pos2, offset) {
    if (!pos1 || !pos2) {
      if (this.zoomBox) {
        this.canvasCoverLayer.removeChild(this.zoomBox)
        this.zoomBox = null
      }
      return
    }
    if (!this.zoomBox) {
      this.zoomBox = document.createElement('div')
      this.zoomBox.classList.add('zoomwindow')
      this.canvasCoverLayer.appendChild(this.zoomBox)
    }
    const left = Math.min(pos1.clientX, pos2.clientX)
    const right = Math.max(pos1.clientX, pos2.clientX)
    const top = Math.min(pos1.clientY, pos2.clientY)
    const bottom = Math.max(pos1.clientY, pos2.clientY)

    this.zoomBox.style.left = left - offset.x + 'px'
    this.zoomBox.style.top = top - offset.y + 'px'
    this.zoomBox.style.width = right - left + 'px'
    this.zoomBox.style.height = bottom - top + 'px'
  }

  /**
   * Mouse button up - zoom
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   * @param {*} resultId the actual result if the click was on a given trace
   * @param {*} stepId the step if the click was on a given trace
   */
  onclick = (evt, coord, resultId, stepId) => {
    if (resultId) {
      this.clicked(resultId, stepId)
    } else if (this.pressed) {
      const originalZoom = this.chartManager.getZoom()
      const originaXLength = originalZoom.right - originalZoom.left
      const originaYLength = originalZoom.bottom - originalZoom.top

      const amountOfXChange = Math.abs(this.startZoomCoord.x - coord.x) / originaXLength
      const amountOfYChange = Math.abs(this.startZoomCoord.y - coord.y) / originaYLength

      if (amountOfXChange > 0.005 && amountOfYChange > 0.005) { // prevent single click zoom
        this.chartManager.zoom(this.startZoomCoord, coord)
      }
    }
    this.zoomBoxDraw(null, null)
    this.pressed = null
    this.startZoomCoord = null
  }

  /**
   * Mouse button down - zoom area start of selection
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   */
  onmousedown = (evt, coord) => {
    switch (evt.button) {
      case 0:
        this.divOffset = {
          x: evt.x - evt.offsetX,
          y: evt.y - evt.offsetY
        }
        this.startZoomCoord = coord
        this.pressed = evt
        break
      default:
        this.chartManager.resetZoom()
    }
  }

  /**
   * Draw a box when mouse selecting a zoom area
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   */
  onmousemove = (evt, coord) => {
    if (this.pressed) {
      this.zoomBoxDraw(evt, this.pressed, this.divOffset)
    }
  }

  /**
   * handle mouse wheel, or touchpad zoom
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   * @returns Nothing
   */
  onmousewheel = (evt, coord) => {
    const sensitivityWheel = 500
    const sensitivityPad = 100

    let deltaY = (evt.deltaY / sensitivityWheel) + 1

    if (evt.ctrlKey) { // Only way to differentiate between touchpad and mousewheel???
      deltaY = (evt.deltaY / sensitivityPad) + 1
    }

    const deltaX = deltaY

    if ((deltaX < 0.5) || (deltaX > 2) || (deltaY < 0.5) || (deltaY > 2)) {
      return // Ignore random very large zooms
    }

    const currentZoom = this.chartManager.getZoom()

    const new1 = {
      x: coord.x - (coord.x - currentZoom.left) * deltaX,
      y: coord.y - (coord.y - currentZoom.top) * deltaY
    }

    const new2 = {
      x: coord.x + (currentZoom.right - coord.x) * deltaX,
      y: coord.y + (currentZoom.bottom - coord.y) * deltaY
    }
    this.chartManager.zoom(new1, new2)
  }

  /**
   * Touchscreen start touch storage of original selection and zoom
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   * @param {*} touchOffsetoffset to correctly calculate zoom area
   */
  touchstart (evt, coord, touchOffset) {
    this.touchStarts = evt.touches
    this.touchStartZoom = this.chartManager.getZoom()
    this.touchStartWindow = this.chartManager.getWindowDimensions()
  }

  /**
   * Support function to standardize the selected corners to always be upper left and lower right
   * @param {*} listOfTouches the events list of touches
   * @returns the standardized coordinates, both wrt the pixel coordinates and the grph coordinates
   */
  normalizeTouches (listOfTouches) {
    if (listOfTouches.length === 1) {
      return {
        lower: { x: listOfTouches[0].x, y: listOfTouches[0].y }
      }
    }
    const minX = Math.min(listOfTouches[0].x, listOfTouches[1].x)
    const minY = Math.min(listOfTouches[0].y, listOfTouches[1].y)
    const maxX = Math.max(listOfTouches[0].x, listOfTouches[1].x)
    const maxY = Math.max(listOfTouches[0].y, listOfTouches[1].y)
    const minCoordinateX = Math.min(listOfTouches[0].coordinateX, listOfTouches[1].coordinateX)
    const minCoordinateY = Math.min(listOfTouches[0].coordinateY, listOfTouches[1].coordinateY)
    const maxCoordinateX = Math.max(listOfTouches[0].coordinateX, listOfTouches[1].coordinateX)
    const maxCoordinateY = Math.max(listOfTouches[0].coordinateY, listOfTouches[1].coordinateY)
    return {
      lower: { x: minX, y: minY },
      upper: { x: maxX, y: maxY },
      lowerCoordinates: { x: minCoordinateX, y: minCoordinateY },
      upperCoordinates: { x: maxCoordinateX, y: maxCoordinateY }
    }
  }

  /**
   * Correct the pixel selection wrt the screen position
   * @param {*} pixelpoint a point on the screen
   * @returns a corrected point in the frame of reference of the display area of the graph
   */
  pixelToScreenRatio (pixelpoint) {
    const touchStartWindow = this.chartManager.getWindowDimensions()
    return {
      x: pixelpoint.x / (touchStartWindow.right - touchStartWindow.left),
      y: pixelpoint.y / (touchStartWindow.bottom - touchStartWindow.top)
    }
  }

  /**
   * Zoom the screen based on a two touch moving selection
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   * @param {*} touchOffset to correctly calculate zoom area
   */
  touchmove (evt, coord, touchOffset) {
    function modifyWithOffset (pointList) {
      const returnList = []
      for (const point of pointList) {
        returnList.push({
          x: point.clientX - touchOffset.x,
          y: point.clientY - touchOffset.y,
          coordinateX: point.internalCoordinates.x,
          coordinateY: point.internalCoordinates.y
        })
      }
      return returnList
    }

    function areaRatios (zoomArea, screen) {
      return {
        x: {
          left: zoomArea.lower.x / screen.width,
          center: (zoomArea.upper.x - zoomArea.lower.x) / screen.width,
          right: (screen.width - zoomArea.upper.x) / screen.width
        },
        y: {
          top: zoomArea.lower.y / screen.height,
          center: (zoomArea.upper.y - zoomArea.lower.y) / screen.height,
          bottom: (screen.height - zoomArea.upper.y) / screen.height
        }
      }
    }

    if (evt.touches.length === 2) {
      const startPoints = this.normalizeTouches(modifyWithOffset(this.touchStarts))
      const currentPoints = this.normalizeTouches(modifyWithOffset(evt.touches))

      const initialRatios = areaRatios(startPoints, this.touchStartWindow)
      const endRatios = areaRatios(currentPoints, this.touchStartWindow)

      const scaleChange = {
        x: initialRatios.x.center / endRatios.x.center,
        y: initialRatios.y.center / endRatios.y.center
      }
      const width = this.touchStartZoom.right - this.touchStartZoom.left
      const height = this.touchStartZoom.bottom - this.touchStartZoom.top

      const windowLeftCoordinate = startPoints.lowerCoordinates.x - endRatios.x.left * width * scaleChange.x
      const windowRightCoordinate = startPoints.upperCoordinates.x + endRatios.x.right * width * scaleChange.x

      const windowTopCoordinate = startPoints.upperCoordinates.y + endRatios.y.top * height * scaleChange.y
      const windowBottomCoordinate = startPoints.lowerCoordinates.y - endRatios.y.bottom * height * scaleChange.y

      const newLower = {
        x: windowLeftCoordinate,
        y: windowBottomCoordinate
      }
      const newUpper = {
        x: windowRightCoordinate,
        y: windowTopCoordinate
      }

      this.chartManager.zoom(newLower, newUpper)
      // this.touchstart(evt, coord)
    }
  }

  touchend (evt, coord, touchOffset) {
    // console.log(coord)
  }

  touchcancel (evt, coord, touchOffset) {
    // console.log(coord)
  }
}
