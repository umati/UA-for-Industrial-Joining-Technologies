import '../../../node_modules/chart.js/dist/chart.umd.js'
import Dataset from './Dataset.mjs'
/**
 * Chartmanager should encapsulate all access to chart.js in order to
 * make it possible to exchange chart component with minimal effort
 */
export default class ChartManager {
  constructor (ctx, traceManager) {
    this.context = ctx
    this.traceManager = traceManager
    /* eslint-disable */
    this.myChart = new Chart(ctx, {
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
          duration: 200
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

    document.getElementById('myChart').onclick = (evt) => {
      const points = this.myChart.getElementsAtEventForMode(evt,
        'nearest', { intersect: true }, true)

      if (points.length) {
        const firstPoint = points[0]
        const dataset = this.myChart.data.datasets[firstPoint.datasetIndex]
        console.log(dataset.resultId)
        console.log(dataset.stepId)
        this.traceManager.clicked(dataset.resultId, dataset.stepId.value)
      }
      // use _datasetIndex and _index from each element of the activePoints array
    }
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
  createDataset (name) {
    const dataset = new Dataset(name)
    this.myChart.data.datasets.push(dataset)
    // this.myChart.data.labels.push(name)
    return dataset
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
   * Pushes this part of the graph in front of the other graphs
   * @param {*} datasets
   */
  putInFront (datasets) {
    this.filterOut(datasets)

    for (const ds of datasets) {
      this.myChart.data.datasets.push(ds)
    }
  }
}
