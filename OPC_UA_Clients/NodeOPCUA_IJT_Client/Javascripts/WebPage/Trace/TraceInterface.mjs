
export default class TraceInterface {

    constructor(container) {
        this.generateHTML(container);
        this.resetColor();
    }
    setTraceSelectEventListener(evtHandler) {
        this.selectTraceEventHandler = evtHandler;
    }
    updateTracesInGUI(allTraces) {
        this.traceDiv.innerHTML = '';
        for (let trace of allTraces) {

            let tracebutton = document.createElement('button');
            tracebutton.classList.add('myButton');
            tracebutton.innerText = trace.displayName
            this.traceDiv.appendChild(tracebutton);
            tracebutton.resultId = trace.result.resultId

            tracebutton.addEventListener('click', this.selectTraceEventHandler);
        }
    }
    
    selectTrace(id) {
        for(let button of this.traceDiv.children) {
            if (button.resultId==id) {
                button.classList.add('myButtonSelected');
            } else {
                button.classList.remove('myButtonSelected');
            }
        }
    }

    setStepSelectEventListener(evtHandler) {
        this.selectStepEventHandler = evtHandler;
    }

    clearSteps() {
        this.stepDiv.innerHTML = '';
        this.addStepInGUI({name:'All', stepId:{value:'all'}});
    }

    addStepInGUI(step) {
        let stepButton = document.createElement('button');
        stepButton.classList.add('myButton');
        stepButton.innerText = step.name;
        this.traceDiv.appendChild(stepButton);
        stepButton.stepId = step.stepId.value;

        stepButton.addEventListener('click', this.selectStepEventHandler);
        this.stepDiv.appendChild(stepButton);
    }

    selectStep(id) {
        for(let button of this.stepDiv.children) {
            if (button.stepId==id) {
                button.classList.add('myButtonSelected');
            } else {
                button.classList.remove('myButtonSelected');
            }
        }
    }

    resetColor() {
        this.hue = 0;
        this.saturation = 100;
        this.lightness = 40;
    }
    getRandomColor() {

        if (this.lightness < 0) {
            this.resetColor();
        }
        return 'hsl(' + (this.hue += 108) + ', 100%, ' + (this.lightness -= 1) + '%)';
    }

    generateHTML(container) {
        function createHeader(container, name) {
            let header = document.createElement('div');
            header.innerText = name;
            header.classList.add('myHeader');
            container.appendChild(header);
        }
        function createTuple(name, right) {
            let outer = document.createElement('div');
            outer.classList.add('kvPair');
            let title = document.createElement('div');
            title.classList.add('kvKey');
            title.innerText = name;
            outer.appendChild(title);
            let content = document.createElement('div');
            content.classList.add('kvValue');
            content.appendChild(right);
            outer.appendChild(content);
            return outer;
        }

        function createSelector(container, name, values, standalone = false) {
            let selector = document.createElement('select');
            selector.classList.add('kvSelect');
            for (let v of values) {
                let option = document.createElement('option');
                option.setAttribute('value', v[0]);
                option.innerText = v[1];
                selector.appendChild(option);
            }
            if (standalone) {
                container.appendChild(selector);
            } else {
                container.appendChild(createTuple(name, selector));
            }
            return selector;
        }

        let backGround = document.createElement('div');
        backGround.classList.add('myInfoArea');
        backGround.classList.add('traceArea');
        container.appendChild(backGround);

        let title = document.createElement('div');
        title.classList.add('myHeader');
        title.innerText = 'Trace';
        backGround.appendChild(title);

        this.canvas = document.createElement('canvas');
        this.canvas.setAttribute('id', 'myChart');
        backGround.appendChild(this.canvas);

        let interfaceArea = document.createElement('div');
        interfaceArea.classList.add('traceButtonArea');
        container.appendChild(interfaceArea);

        let trace = document.createElement('div');
        trace.classList.add('myInfoArea');
        interfaceArea.appendChild(trace);

        createHeader(trace, 'Traces');

        this.traceDiv = document.createElement('div');
        trace.appendChild(this.traceDiv);

        //this.traceDiv.classList.add('traceList');

        createHeader(trace, 'Steps');

        this.stepDiv = document.createElement('div');
        trace.appendChild(this.stepDiv);

        /*
        this.zoomButton = document.createElement('button');
        this.zoomButton.classList.add('myButton');
        this.zoomButton.innerText = 'Zoom'
        trace.appendChild(this.zoomButton);*/

        let view = document.createElement('div');
        view.classList.add('myInfoArea');
        view.classList.add('thinView');
        //view.classList.add('smallSettingArea');
        interfaceArea.appendChild(view);

        createHeader(view, 'View');

        this.traceTypeSelect = createSelector(view, 'View type', [['toa', 'Torque over angle'], ['tot', 'Torque over time']], true);
        this.absoluteSelect = createSelector(view, 'Torque values', [['normal', 'Normal'], ['absolute', 'Absolute']], true);
        //this.xyz = createSelector(interfaceArea, 'Fade old', [['toa','Torque over angle'],['tot','Torque over time']]);

        this.valueShower = createSelector(view, 'Show values', [['no', 'Hide values'], ['yes', 'Show values']], true);
        this.limitShower = createSelector(view, 'Show limits', [['no', 'Hide limits'], ['yes', 'Show limits']], true);
    
        this.deleteButton = document.createElement('button');
        this.deleteButton.classList.add('myButton');
        this.deleteButton.innerText = 'Delete'
        view.appendChild(this.deleteButton);

        this.alignButton = document.createElement('button');
        this.alignButton.classList.add('myButton');
        this.alignButton.innerText = 'Align'
        view.appendChild(this.alignButton);


    
    }
}