import ChartManager from './ChartHandler.mjs';
import Dataset from './Dataset.mjs';

export default class SingleTraceData {

    constructor(result, owner) {
        this.steps = [];
        this.result = result;
        this.resultId = result.resultId;
        this.displayOffset = 0;
        this.owner = owner;
        this.selected=false;
        this.highLights=[];
        this.displayName =result.creationTime.substr(11, 5);
    }

    get chartManager() {
        return this.owner.chartManager;
    }

    
    get showValuesSelected() {
        return this.owner.showValuesSelected;
    }

    get showLimitSelected() {
        return this.owner.showLimitSelected;
    }

    addStep(step) {
        this.steps.push(step);
    }

    generateTrace() {
        for (let traceStep of this.steps) {
            let color = traceStep.color;
            let cm = this.chartManager;

            let dataset = cm.createDataset(traceStep.name);

            dataset.show();
            dataset.setResultId(this.result.resultId);
            dataset.setStepId(traceStep.stepId);
            dataset.setBackgroundColor(color);
            dataset.setBorderColor(color);
            dataset.setBorderWidth(1);

            traceStep.dataset = dataset;
            traceStep.calculateData();
            traceStep.createPoints(color);
            traceStep.calculatePoints();
        }
        return; 
    }

    highLight(){
        this.deHighLight()
        for (let traceStep of this.steps) {
            traceStep.highLight();
        }
    }

    deHighLight(){
        for (let traceStep of this.steps) {
            traceStep.deHighLight();
        }
    }

    select() {
        this.selected=true;
        this.highLight()
    }

    deselect() {
        this.selected=false;
        this.deHighLight()
        for (let traceStep of this.steps) {
            traceStep.deselect();
        }
    }

    refreshTraceData() {
        for (let traceStep of this.steps) {
            traceStep.calculateData();
            traceStep.calculatePoints();
        }
    }

    findStepByStepId(id) {
        if (id == 'all') {
            return 'all';
        }
        return this.steps.find((element) => {
            return element.stepId.value == id
        }
        );
    }

    findStepByProgramStepId(id) {
        if (id == 'all') {
            return 'all';
        }
        return this.steps.find((element) => {
            return element.stepId.link.programStepId == id
        }
        );
    }


}
