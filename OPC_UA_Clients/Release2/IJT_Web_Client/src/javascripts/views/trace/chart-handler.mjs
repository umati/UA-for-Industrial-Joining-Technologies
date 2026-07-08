/* global Chart */
import '../../../../node_modules/chart.js/dist/chart.umd.js'
import Graphic from './graphic.mjs'
import { createOptionalTraceExtensionLoader } from './optional-trace-extension-loader.mjs'

const LIMIT_ENDPOINT_ARROW_LENGTH = 14
const ZOOM_DEBOUNCE_MS = 100
const limitGeometryExtension = createOptionalTraceExtensionLoader('../envelope/core/limit-curve-geometry.mjs')

/**
 * Chartmanager should encapsulate all access to chart.js in order to
 * make it possible to exchange chart component with minimal effort
 */
export default class ChartManager {
  constructor (traceManager, context, debugSourceText, options = {}) {
    this.afterUpdateCallbacks = []
    this.traceManager = traceManager
    this.context = context
    this.debugSourceText = debugSourceText
    this.lastTimeZoom = window.performance.now()
    this.pressed = null
    this.dummy = 0

    const customPlugin = {
      id: 'customPlugin',
      afterUpdate (chart) {
        const callbacks = chart.config.options.plugins.customPluginContext?.afterUpdateCallbacks
        if (Array.isArray(callbacks)) {
          for (const callback of callbacks) {
            if (callback) {
              callback(chart)
            }
          }
        }
      }
    }
    customPlugin.context = this

    const arrowPlugin = {
      id: 'arrowPlugin',
      beforeDatasetDraw (chart, args) {
        const dataset = chart.data.datasets[args.index]
        if (!dataset?.envelopeMetaData || dataset.envelopeMetaData.type !== 'shell') {
          return
        }
        const highlightColor = dataset.envelopeMetaData.highlightColor
        if (typeof highlightColor !== 'string' || highlightColor.trim().length === 0) {
          return
        }
        const points = chart.getDatasetMeta(args.index)?.data || []
        if (points.length < 2) {
          return
        }
        const lineWidth = Number(dataset.envelopeMetaData.highlightLineWidth)
        const ctx = chart.ctx
        ctx.save()
        ctx.beginPath()
        let didMove = false
        for (const point of points) {
          const x = Number(point?.x)
          const y = Number(point?.y)
          if (!Number.isFinite(x) || !Number.isFinite(y)) {
            didMove = false
            continue
          }
          if (!didMove) {
            ctx.moveTo(x, y)
            didMove = true
          } else {
            ctx.lineTo(x, y)
          }
        }
        ctx.strokeStyle = highlightColor
        ctx.lineWidth = Number.isFinite(lineWidth) ? lineWidth : 7
        ctx.lineJoin = 'round'
        ctx.lineCap = 'round'
        ctx.stroke()
        ctx.restore()
      },
      afterDatasetDraw (chart, args, options) {
        // Get the last two points of the dataset
        const ctx = chart.ctx

        const dataset = chart.data.datasets[args.index]
        if (!dataset.envelopeMetaData || dataset.envelopeMetaData.type !== 'envelope') {
          return
        }
        const direction = dataset.envelopeMetaData.direction
        const data = dataset.data
        const extension = limitGeometryExtension.get()
        const resolveLimitEndpoints = extension.resolveLimitEndpoints ||
          (() => ({ start: null, end: null }))
        const hasCompleteEndpointPair = extension.hasCompleteEndpointPair ||
          (() => false)
        const { start, end } = resolveLimitEndpoints(data, direction)

        if (hasCompleteEndpointPair(end)) {
          const x1 = chart.scales.x.getPixelForValue(end.edgeClose.x)
          const y1 = chart.scales.y.getPixelForValue(end.edgeClose.y)
          const x2 = chart.scales.x.getPixelForValue(end.edge.x)
          const y2 = chart.scales.y.getPixelForValue(end.edge.y)

          // Draw the arrow
          const endArrowScale = Number(dataset?.envelopeMetaData?.endArrowScale)
          const arrowLength = LIMIT_ENDPOINT_ARROW_LENGTH * (Number.isFinite(endArrowScale) ? endArrowScale : 1)
          const angle = Math.atan2(y2 - y1, x2 - x1)

          ctx.save()
          ctx.beginPath()
          ctx.moveTo(x2, y2)
          ctx.lineTo(x2 - arrowLength * Math.cos(angle - Math.PI / 6), y2 - arrowLength * Math.sin(angle - Math.PI / 6))
          ctx.moveTo(x2, y2)
          ctx.lineTo(x2 - arrowLength * Math.cos(angle + Math.PI / 6), y2 - arrowLength * Math.sin(angle + Math.PI / 6))
          const configuredArrowColor = dataset?.envelopeMetaData?.endArrowColor || dataset?.envelopeMetaData?.arrowColor
          const configuredArrowLineWidth = Number(dataset?.envelopeMetaData?.endArrowLineWidth ?? dataset?.envelopeMetaData?.arrowLineWidth)
          ctx.strokeStyle = configuredArrowColor || dataset.borderColor || options.color || 'red'
          ctx.lineWidth = Number.isFinite(configuredArrowLineWidth) ? configuredArrowLineWidth : (options.lineWidth || 2)
          ctx.stroke()
          ctx.restore()
        }

        if (hasCompleteEndpointPair(start)) {
          const x1 = chart.scales.x.getPixelForValue(start.edgeClose.x)
          const y1 = chart.scales.y.getPixelForValue(start.edgeClose.y)
          const x2 = chart.scales.x.getPixelForValue(start.edge.x)
          const y2 = chart.scales.y.getPixelForValue(start.edge.y)

          // Draw the arrow
          const startArrowScale = Number(dataset?.envelopeMetaData?.startArrowScale)
          const arrowLength = LIMIT_ENDPOINT_ARROW_LENGTH * (Number.isFinite(startArrowScale) ? startArrowScale : 1)
          const angle = Math.atan2(y2 - y1, x2 - x1)

          ctx.save()
          ctx.beginPath()
          ctx.moveTo(x2, y2)
          ctx.lineTo(x2 - arrowLength * Math.cos(angle - Math.PI / 2),
            y2 - arrowLength * Math.sin(angle - Math.PI / 2))
          ctx.moveTo(x2, y2)
          ctx.lineTo(x2 - arrowLength * Math.cos(angle + Math.PI / 2),
            y2 - arrowLength * Math.sin(angle + Math.PI / 2))
          const configuredArrowColor = dataset?.envelopeMetaData?.startArrowColor || dataset?.envelopeMetaData?.arrowColor
          const configuredArrowLineWidth = Number(dataset?.envelopeMetaData?.startArrowLineWidth ?? dataset?.envelopeMetaData?.arrowLineWidth)
          ctx.strokeStyle = configuredArrowColor || dataset.borderColor || options.color || 'red'
          ctx.lineWidth = Number.isFinite(configuredArrowLineWidth) ? configuredArrowLineWidth : (options.lineWidth || 2)
          ctx.stroke()
          ctx.restore()
        }
      }
    }
    // arrowPlugin.context = this

    const chartPlugins = Array.isArray(options.chartPlugins)
      ? options.chartPlugins.filter(Boolean)
      : []

    this.myChart = new Chart(context, {
      type: 'line',
      data: {
        datasets: [],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
          customPlugin: true,
          arrowPlugin: true,
          customPluginContext: this,
        },
        animation: {
          duration: 200,
        },
        scales: {
          y: {
            type: 'linear',
          },
          x: {
            type: 'linear',
          },
        },
      },
      plugins: [customPlugin, arrowPlugin, ...chartPlugins],
    })

    // this.myChart.options.plugins.push(customPlugin)

    this.myChart.afterUpdateCallbacks = []

    this.context.onmousedown = (evt) => {
      // console.log(this.pixelToValue(evt))
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
      y: offsets.top + this.myChart.chartArea.top,
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
    const axis = this.myChart?.scales
    if (!axis || axis.x === undefined) {
      return
    }
    return {
      x: axis.x.getPixelForValue(value.x),
      y: axis.y.getPixelForValue(value.y),
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
      y: this.myChart.scales?.y?.getValueForPixel(canvasPosition.y),
    }
  }

  canvasPixelPosition (pos) {
    return Chart.helpers.getRelativePosition(pos, this.myChart)
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

    if (window.performance.now() - this.lastTimeZoom > ZOOM_DEBOUNCE_MS) {
      this.lastTimeZoom = window.performance.now()
      this.myChart.update()
    }
  }

  /**
   * Set only x-axis zoom limits and keep y-axis auto-scaling unchanged
   * @param {number} minX minimum x value in view
   * @param {number} maxX maximum x value in view
   */
  setXZoom (minX, maxX) {
    const ticksX = this.myChart?.config?.options?.scales?.x
    if (ticksX) {
      ticksX.min = minX
      ticksX.max = maxX
    }

    const scaleX = this.myChart?.scales?.x
    if (scaleX) {
      scaleX.min = minX
      scaleX.max = maxX
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
      bottom: this.myChart.scales.y.max,
    }
  }

  getWindowDimensions () {
    return this.myChart.chartArea
  }

  /**
   * Enforce the graph to redraw itself
   */
  update (mode = 'none') {
    this.myChart.update(mode)
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
    if (typeof graphic.getAllDatasets === 'function') {
      this.filterOut(graphic.getAllDatasets())
      return
    }
    this.filterOut([graphic.mainDataset, graphic.highlightDataset])
    for (const value of Object.values(graphic.datasetMapping)) {
      this.filterOut([value.valueDataset, value.targetDataset, value.limitsDataset])
    }
  }

  clearTraceDatasets () {
    this.myChart.data.datasets = this.myChart.data.datasets.filter((dataset) => {
      return dataset?.envelopeMetaData?.type === 'envelope'
    })
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
    const limitDataSet = {
      borderColor: borderColour,
      borderWidth: 1,
      fill: startOrEnd,
      label: 'limit',
      backgroundColor: areaColour,
      pointRadius: 0,
      pointHoverRadius: 0,
      pointHitRadius: 0,
      pointBorderColor: borderColour,
      pointBackgroundColor: borderColour,
      data: [],
      envelopeMetaData: {
        type: 'envelope',
        direction: 1,
      }
    }

    this.myChart.data.datasets.push(limitDataSet)
    return this.myChart.data.datasets[this.myChart.data.datasets.length - 1]
  }

  afterUpdateSubscribe (callback) {
    this.afterUpdateCallbacks.push(callback)
    return () => {
      this.afterUpdateCallbacks = this.afterUpdateCallbacks.filter((item) => item !== callback)
    }
  }
}
