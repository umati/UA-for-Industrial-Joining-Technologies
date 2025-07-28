import '../../../node_modules/chart.js/dist/chart.umd.js'
import Graphic from './Graphic.mjs'
/**
 * Chartmanager should encapsulate all access to chart.js in order to
 * make it possible to exchange chart component with minimal effort
 */
export default class ChartManager {
  constructor (traceManager, context) {
    this.traceManager = traceManager
    this.context = context
    this.traceManager = traceManager
    this.lastTimeZoom = window.performance.now()
    this.pressed = null
    this.dummy = 0
    this.myChart = new Chart(context, { // eslint-disable-line
      type: 'line',
      data: {
        datasets: []
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        animation: {
          duration: 200,
          onComplete: function () {
            console.log('YYY Chart rendering is complete!')
            // Add your custom logic here
          }
        },
        scales: {
          y: {
            type: 'linear'
          },
          x: {
            type: 'linear'
          }
        }
      }
    })

    this.context.onmousedown = (evt) => {
      this.traceManager.onmousedown(evt, this.pixelToValue(evt))
    }

    this.context.addEventListener('mousemove', (evt) => {
      evt.preventDefault()
      this.traceManager.onmousemove(evt, this.pixelToValue(evt))
    })

    this.context.addEventListener('wheel', (evt) => {
      evt.preventDefault()
      this.traceManager.onmousewheel(evt, this.pixelToValue(evt))
    })

    this.context.addEventListener('touchstart', (evt) => {
      // console.log('x: ' + Math.round(evt.touches[0].clientY))
      // console.log('y1: ' + Math.round(newPos.offsetX))
      for (const touch of evt.touches) {
        touch.internalCoordinates = this.pixelToValue(touch)
      }
      this.traceManager.touchstart(evt, this.pixelToValue(evt), this.getTouchOffset())
    })

    this.context.addEventListener('touchend', (evt) => {
      this.traceManager.touchend(evt, this.pixelToValue(evt), this.getTouchOffset())
    })

    this.context.addEventListener('touchcancel', (evt) => {
      this.traceManager.touchcancel(evt, this.pixelToValue(evt), this.getTouchOffset())
    })

    // this.context.style.border = '2px solid red'
    this.context.addEventListener('touchmove', (evt) => {
      evt.preventDefault()
      for (const touch of evt.touches) {
        touch.internalCoordinates = this.pixelToValue(touch)
      }
      this.traceManager.touchmove(evt, this.pixelToValue(evt), this.getTouchOffset())
    })
  }

  getTouchOffset () {
    const offsets = this.context.getBoundingClientRect()
    return {
      x: offsets.left + this.myChart.chartArea.left,
      y: offsets.top + this.myChart.chartArea.top
    }
  }

  /**
   * Takes a value {x: ?, y: ??} in the coordinate system and return
   * its pixel position on the canvas
   * @date 3/12/2024 - 1:28:39 PM
   *
   * @param {*} value a graph position object containing an x and a y value
   * @returns {{ x: any; y: any; }} a pixel position on the canvas
   */
  valueToPixel (value) {
    this.dummy++
    const axis = this.myChart.scales
    return {
      x: axis.x.getPixelForValue(value.x),
      y: axis.y.getPixelForValue(value.y)
    }
  }

  /**
   * Takes a value {x: ?, y: ??} pixel position on the canvas and return
   * its graph position object
   * @date 3/12/2024 - 1:31:18 PM
   *
   * @param {*} pos a pixel position on the canvas
   * @returns {{ x: any; y: any; }}  a graph position object
   */
  pixelToValue (pos) {
    this.dummy++
    const canvasPosition = this.canvasPixelPosition(pos)
    return {
      x: this.myChart.scales?.x?.getValueForPixel(canvasPosition.x),
      y: this.myChart.scales?.y?.getValueForPixel(canvasPosition.y)
    }
  }

  canvasPixelPosition (pos) {
    return Chart.helpers.getRelativePosition(pos, this.myChart) // eslint-disable-line
  }

  /**
   * zoom in to an area given the coordinates in the graph
   * @date 3/14/2024 - 11:05:19 AM
   *
   * @param {*} coord1 one corner position
   * @param {*} coord2 the other corner position
   */
  zoom (coord1, coord2) {
    const minX = Math.min(coord1.x, coord2.x)
    const maxX = Math.max(coord1.x, coord2.x)
    const minY = Math.min(coord1.y, coord2.y)
    const maxY = Math.max(coord1.y, coord2.y)

    const ticksX = this.myChart.config.options.scales.x
    ticksX.min = minX
    ticksX.max = maxX

    const ticksY = this.myChart.config.options.scales.y
    ticksY.min = minY
    ticksY.max = maxY

    this.myChart.scales.x.min = minX
    this.myChart.scales.x.max = maxX
    this.myChart.scales.y.min = minY
    this.myChart.scales.y.max = maxY

    // console.log('heh 1 ' + this.myChart.scales.x.min)

    if (window.performance.now() - this.lastTimeZoom > 100) {
      this.lastTimeZoom = window.performance.now()
      this.myChart.update()
    }
  }

  /**
   * reset zoom
   * @date 3/14/2024 - 11:06:11 AM
   */
  resetZoom () {
    const ticks = this.myChart.config.options.scales.x
    ticks.min = null
    ticks.max = null

    const ticksY = this.myChart.config.options.scales.y
    ticksY.min = null
    ticksY.max = null
    this.myChart.update()
  }

  /**
   * Return the corner positions of the currently shown part of the graph area
   * @date 3/14/2024 - 11:06:37 AM
   *
   * @returns {{ xmin: any; xmax: any; ymin: any; ymax: any; }}
   */
  getZoom () {
    return {
      left: this.myChart.scales.x.min,
      right: this.myChart.scales.x.max,
      top: this.myChart.scales.y.min,
      bottom: this.myChart.scales.y.max
    }
  }

  getWindowDimensions () {
    return this.myChart.chartArea
  }

  /**
   * Enforce the graph to redraw itself
   */
  update () {
    this.myChart.update()
  }

  /**
   * Create a new dataset representing a part of a graph
   * @param {*} name
   * @returns
   */
  createGraphic (name, resultId, stepId, color) {
    const graphic = new Graphic(name, resultId, stepId, color)
    this.myChart.data.datasets.push(graphic.mainDataset)

    // this.myChart.data.datasets.push(graphic.highlightDataset)
    return graphic
  }

  /**
   * Create a step values graphical representation
   * @date 3/5/2024 - 10:51:13 AM
   *
   * @param {*} value the step value
   * @param {*} point the (x, y) position of the value
   * @param {*} color the intended color
   * @param {*} graphic the graphic representation of the step
   */
  createStepValue (value, points, color, graphic) {
    const datasets = graphic.createStepValue(value, points, color)

    this.myChart.data.datasets.push(datasets.valueDataset)
    this.myChart.data.datasets.push(datasets.limitsDataset)
    this.myChart.data.datasets.push(datasets.targetDataset)
  }

  /**
   *  Remove some of the datasets from the drawing area
   * @param {*} selectedDataSets
   */
  filterOut (selectedDataSets) {
    this.myChart.data.datasets = this.myChart.data.datasets.filter((e) => {
      return selectedDataSets.indexOf(e) < 0
    })
  }

  /**
   *  Remove some of the datasets from the drawing area
   * @param {*} selectedDataSets
   */
  filterOutGraphic (graphic) {
    this.filterOut([graphic.mainDataset, graphic.highlightDataset])
    for (const value of Object.values(graphic.datasetMapping)) {
      this.filterOut([value.valueDataset, value.targetDataset, value.limitsDataset])
    }
  }

  /**
   * Pushes this part of the graph in front of the other graphs
   * @param {*} datasets
   */
  putInFront (datasets) {
    this.filterOut(datasets)

    for (const ds of datasets) {
      this.myChart.data.datasets.push(ds)
    }
  }

  newLimit (borderColour, areaColour, startOrEnd) {
    const upperLimit = {
      borderColor: borderColour,
      borderWidth: 1,
      fill: startOrEnd,
      label: 'limit',
      backgroundColor: areaColour,
      pointBorderColor: 'transparent',
      pointBackgroundColor: 'transparent',
      data: []
    }

    this.myChart.data.datasets.push(upperLimit)
    const upperDataCurve = this.myChart.data.datasets[this.myChart.data.datasets.length - 1]
    return upperDataCurve
  }
}
