/**
 * Supportclass to help encapsulate the chart package
 */
export default class Dataset {

    constructor(name) {
        this.label = name;
        this.radius=0;
        this.borderWidth = 1;
    }

    show() {
        this.hidden = false;
    }
    hide() {
        this.hidden = true;
    }

    setBackgroundColor(color) {
        this.backgroundColor = color;
    }
    setRadius(radius) {
        this.radius = radius;
    }
    setBorderColor(color) {
        this.borderColor = color;
    }
    setBorderWidth(width) {
        this.borderWidth = width;
    }
    setPoints(points) {
        this.data = points;
    }
    
    setResultId(id){
        this.resultId=id;
    }
    
    setStepId(id){
        this.stepId=id;
    }
    
    select() {
        this.borderWidth = 2;
    }
    
    deselect() {
        this.borderWidth = 1;
    }
}