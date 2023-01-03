import Chart from '../../../node_modules/chart.js/auto/auto.js';
import Dataset from './Dataset.mjs';

export default class ChartManager {

    constructor(ctx, traceManager) {
        this.context=ctx;
        this.traceManager=traceManager;
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
                },
            }
        });
        
        document.getElementById("myChart").onclick = (evt)=>{
            const points = this.myChart.getElementsAtEventForMode(evt, 
                'nearest', { intersect: true }, true);

            if (points.length) {
                const firstPoint = points[0];
                const dataset = this.myChart.data.datasets[firstPoint.datasetIndex];
                console.log(dataset.resultId);
                console.log(dataset.stepId);
                this.traceManager.clicked(dataset.resultId, dataset.stepId.value);
            }
            // use _datasetIndex and _index from each element of the activePoints array
        };
    }

    update() {
        this.myChart.update()
    }

    createDataset(name) {
        let dataset = new Dataset(name);
        this.myChart.data.datasets.push(dataset);
        //this.myChart.data.labels.push(name);
        return dataset;
    }
    filterOut(selectedDataSets) {
        this.myChart.data.datasets = this.myChart.data.datasets.filter((e) => {
            return selectedDataSets.indexOf(e) < 0
        });
    }

    putInFront(datasets) {
        this.filterOut(datasets);

        for (let ds of datasets) {
            this.myChart.data.datasets.push(ds);
        }
    }

}
