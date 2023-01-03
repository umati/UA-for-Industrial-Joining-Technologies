import IJTBaseModel from './IJTBaseModel.mjs';

// The purpose of this class is to handle the actual subscription or reading of a value and via socketIO send the result to the webpage
export default class ResultDataModel extends IJTBaseModel {
    constructor(parameters, modelManager) { 
        let castMapping= { 
            'processingTimes': 'ProcessingTimesDataType',
            'tags':'TagDataType',
            'resultContent' : 'TighteningResultDataType'
        }
        super(parameters, modelManager,castMapping);
        
        let event = new CustomEvent(
            "newResultReceived",
            {
                detail: {
                    result: this,
                    trace: this.resultContent.trace,
                },
                bubbles: true,
                cancelable: true
            }
        );

        let serverDiv = document.getElementById('connectedServer');
        serverDiv.dispatchEvent(event);

    }

}
