

export default class SocketHandler {
    constructor(socket) {
        this.socket = socket;
        this.callMapping = {};
        this.failMapping = {};
        this.mandatoryLists= {};
        this.browseList = [];
        this.readList = [];
    }


    read(nodeId, callback) {
        this.callMapping[nodeId] = callback;
        this.socket.emit('read', nodeId);
    }

    browse(nodeId, callback, details) {
        this.callMapping[nodeId] = callback;
        this.socket.emit('browse', nodeId, details);
    }

    browsePromise(nodeId, details) {
        return new Promise((resolve,reject) => {
            this.callMapping[nodeId] = resolve;
            this.failMapping[nodeId] = reject;
            this.socket.emit('browse', nodeId, details);
        });
    }

    registerMandatory(typeList, callback) {
        if (!this.mandatoryLists[typeList]) {
            this.mandatoryLists[typeList]=[];
        }
        this.mandatoryLists[typeList].push(callback);

        this.socket.on(typeList, (msg) => {
            
            let returnNode = this.applyAll(this.mandatoryLists[typeList], msg);

            if (msg && msg.callernodeid) {
            let callbackFunction = this.callMapping[msg.callernodeid];
            this.callMapping[msg.callernodeid] = null;
            if (callbackFunction) {
                callbackFunction(msg, returnNode);
            }
        }
        });
    }
    
    applyAll(functionList, msg) {
        let returnValue;
        for (let f of functionList) {
            let nodeResult = f(msg);
            if (nodeResult) {
                returnValue = nodeResult;
            }
        }
        return returnValue;
    }

}

