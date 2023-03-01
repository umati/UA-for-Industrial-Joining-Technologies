import ChartManager from './ChartHandler.mjs';
import SingleTraceData from './SingleTraceData.mjs';

export default class Step {

    constructor(step, owner) {
        this.name = step.stepResultId.link.name;
        this.stepId = step.stepResultId;
        this.color = '',
            this.time = null,
            this.torque = null,
            this.angle = null,
            this.hidden = false;
        this.values = step.stepResultId.link.stepResultValues;
        this.last = {};
        this.datasetMapping = {};
        this.startTimeOffset = step.startTimeOffset;
        this.dataset = [];
        this.owner = owner;
    }

    get displayOffset() {
        return this.owner.displayOffset;
    }
    get xDimensionName() {
        return this.owner.owner.xDimensionName;
    }
    get yDimensionName() {
        return this.owner.owner.yDimensionName;
    }

    get absoluteFunction() {
        return this.owner.owner.absoluteFunction;
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


    /////////////////////////////////// CURVE MANAGEMENT ////////////////////////////////////////////
    calculateData() {
        let xValues = this[this.xDimensionName];
        let yValues = this[this.yDimensionName].map(this.absoluteFunction);

        if (this.xDimensionName == 'time') {
            xValues = xValues.map((x) => { return x + this.startTimeOffset });
        }
        this.dataset.data = [];
        if (xValues.length != yValues.length) {
            throw 'data in step ' + this.name + ' is not the same in X and Y lists';
        }
        for (let i = 0; i < xValues.length; i++) {
            this.dataset.data.push({
                x: xValues[i] - this.displayOffset,
                y: yValues[i],
            });
        }

        this.last.x = xValues[xValues.length - 1];
        this.last.y = yValues[yValues.length - 1];
        if (this.highLightDataset) {
            this.highLightDataset.data=this.dataset.data
        }

        return;
    }


    /////////////////////////////////// POINT MANAGEMENT ////////////////////////////////////////////
    createPoints(color) {
        for (let value of this.values) {
            let point = this.interpretPoint(value);
            let datasets = this.createDatasets(value.name, point, color);

            this.datasetMapping[value.valueId] = {
                'valueDataset': datasets.value,
                'limitsDataset': datasets.limits,
                'targetDataset': datasets.target
            }
        }
    }

    calculatePoints() {
        for (let value of this.values) {
            let hide = this.hidden;
            if ((this.xDimensionName == 'angle' && value.physicalQuantity == 1) ||
                (this.xDimensionName == 'time' && value.physicalQuantity == 3) ||
                (!this.showValuesSelected)) {
                hide = true;
            }

            this.updatePoint(value, hide);
        }
    }

    updatePoint(value, hide) {
        let points = this.interpretPoint(value);
        this.datasetMapping[value.valueId].valueDataset.data = [points.value]
        this.datasetMapping[value.valueId].limitsDataset.data = points.limits
        this.datasetMapping[value.valueId].targetDataset.data = [points.target]

        this.displayValuesAccordingToSettings(value, !hide, this.showLimitSelected);
    }



    interpretPoint(value) {
        let x, y, xHigh, yHigh, xLow, yLow, xTarget, yTarget, xOffset = 0;
        switch (value.physicalQuantity) {
            case 1: // Time
                x = value.value;
                xHigh = value.highLimit;
                xLow = value.lowLimit;
                xTarget = value.targetValue;
                xOffset = this.startTimeOffset;
                break;
            case 2: // Torque
                y = value.value;
                yHigh = value.highLimit;
                yLow = value.lowLimit;
                yTarget = value.targetValue;
                break;
            case 3: // Angle
                x = value.value;
                xHigh = value.highLimit;
                xLow = value.lowLimit;
                xTarget = value.targetValue;
                if (this.angle.length > 0) {
                    xOffset = this.angle[0];
                }
                break;
            case 11: // Current
                break;
            default:
                throw "Unknown physicalQuantity in trace"
        }

        // Guess where on the non described dimension it should be put
        if (y == null) {
            y = -1;
            yHigh = null;
            yLow = null;
            yTarget = null;
        }
        if (x == null) {
            x = this.last.x;
            xHigh = null;
            xLow = null;
            xTarget = null;
        }
        // Avoid drawing spans when high and low are not set
        if (yHigh == 0 && yLow == 0) {
            yHigh = null;
            yLow = null;
        }
        if (xHigh == 0 && xLow == 0) {
            xHigh = null;
            xLow = null;
        }

        let limits = [];
        let value2;
        let target;
        let limitYOffset = 5;
        if (xHigh != null) {
            limits.push({ x: xHigh - this.displayOffset + xOffset, y: y + limitYOffset, name: '[limit]', type: 'limit' });
        }
        if (yHigh != null) {
            limits.push({ x: x - this.displayOffset + xOffset, y: yHigh + limitYOffset, name: '[limit]', type: 'limit' });
        }
        value2 = { x: x - this.displayOffset + xOffset, y: y, type: '' };

        if (xLow != null) {
            limits.push({ x: xLow - this.displayOffset + xOffset, y: y + limitYOffset, name: '[limit]', type: 'limit' });
        }
        if (yLow != null) {
            limits.push({ x: x - this.displayOffset + xOffset, y: yLow + limitYOffset, name: '[limit]', type: 'limit' });
        }
        if (xTarget != null) {
            target = { x: xTarget - this.displayOffset + xOffset, y: y + limitYOffset, name: '[target]', type: 'target' };
        }
        if (yTarget != null) {
            target = { x: x - this.displayOffset + xOffset, y: yTarget + limitYOffset, name: '[target]', type: 'target' };
        }

        return {
            target: target,
            limits: limits,
            value: value2,
            name: value.name,
        };
    }

    createDatasets(name, points, color) {
        let res = {};
        function handleGroup(list, tag, chartManager) {
            let dataset = chartManager.createDataset(name + tag);
            dataset.show();
            dataset.setBackgroundColor(color);
            dataset.setBorderColor("gray");
            dataset.setBorderWidth(1);
            dataset.setRadius(3);
            dataset.setPoints(list);
            return dataset;
        }

        res.value = handleGroup([points.value], '', this.chartManager);
        res.limits = handleGroup(points.limits, '[limit]', this.chartManager);
        res.target = handleGroup([points.target], '[target]', this.chartManager);

        return res;
    }

    ///////////////////////////////////////////////////////

    delete() {          
        for (const [key, value] of Object.entries(this.datasetMapping)) {
        this.chartManager.filterOut([value.valueDataset]);
        this.chartManager.filterOut([value.targetDataset]);
        this.chartManager.filterOut([value.limitsDataset]);
        this.chartManager.filterOut([this.highLightDataset]);
        this.chartManager.filterOut([this.dataset]);
        }
    }

    select() {
        this.dataset.select();
    }
    deselect() {
        this.dataset.deselect();
    }

    highLight() {
        if (!this.highLightDataset) {
            this.highLightDataset = this.chartManager.createDataset('highlight');
            let color = "rgba( 255, 255, 180, 0.4 )";
            this.highLightDataset.setBackgroundColor(color);
            this.highLightDataset.setBorderColor(color);
            this.highLightDataset.setBorderWidth(5);
        }
        this.highLightDataset.setPoints(this.dataset.data);
        if(this.hidden) {
            this.highLightDataset.hide();

        } else {
            this.highLightDataset.show();
        }
    }

    deHighLight() {
        if(this.highLightDataset) {
        this.highLightDataset.hide();
        }
    }


    createHighlightDataset() {
        if (this.hidden) {
            return;
        }
        let dataset = this.chartManager.createDataset('highlight');
        dataset.show();
        let color = "rgba( 255, 255, 180, 0.4 )";
        dataset.setBackgroundColor(color);
        dataset.setBorderColor(color);
        dataset.setBorderWidth(5);
        dataset.setPoints(this.dataset.data);
        return dataset;

    }

    ///////////////////////////////////////////////////////

    hideStepTrace() {
        this.dataset.hide();
        this.hidden = true;
        this.hideValues();
    }

    showStepTrace() {
        this.dataset.show();
        this.hidden = false;
        for (let value of this.values) {
            this.displayValuesAccordingToSettings(value, this.showValuesSelected, this.showLimitSelected);
        }
    }


    hideValues() {
        for (let value of this.values) {
            this.hideValue(value);
        }
    }

    hideValue(value) {
        this.datasetMapping[value.valueId].valueDataset.hide();
        this.datasetMapping[value.valueId].limitsDataset.hide();
        this.datasetMapping[value.valueId].targetDataset.hide();
    }

    displayValuesAccordingToSettings(value, showValue, showLimits) {
        this.hideValue(value);
        if (showValue) {
            this.datasetMapping[value.valueId].valueDataset.show();
            if (showLimits) {
                this.datasetMapping[value.valueId].limitsDataset.show();
                this.datasetMapping[value.valueId].targetDataset.show();

            }
        }
    }
}