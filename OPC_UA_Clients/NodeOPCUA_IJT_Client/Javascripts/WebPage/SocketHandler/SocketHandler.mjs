

export default class SocketHandler {
    constructor(socket) {
        this.socket = socket;
        this.callMapping = {};
        this.failMapping = {};
        this.mandatoryLists = {};
        this.browseList = [];
        this.readList = [];
        this.uniqueId = 1;
        this.registerMandatory('readresult');
        this.registerMandatory('browseresult');
        this.registerMandatory('pathtoidresult');
    }


    read(nodeId, callback) {
        this.uniqueId++;
        this.callMapping[this.uniqueId] = callback;
        this.socket.emit('read', this.uniqueId, nodeId);
    }

    browse(nodeId, callback, details) {
        this.uniqueId++;
        this.callMapping[this.uniqueId] = callback;
        this.socket.emit('browse', this.uniqueId, nodeId, details);
    }

    pathtoid(nodeId, path, callback) {
        this.uniqueId++;
        this.callMapping[this.uniqueId] = callback;
        this.socket.emit('pathtoid', this.uniqueId, nodeId, path);
    }

    /*
    browsePromise(nodeId, details) {
        return new Promise((resolve,reject) => {
            this.callMapping[nodeId] = resolve;
            this.failMapping[nodeId] = reject;
            this.socket.emit('browse', nodeId, details);
        });
    }*/

    registerMandatory(typeList, callback) {
        if (!this.mandatoryLists[typeList]) {
            this.mandatoryLists[typeList] = [];
        }
        if (this.mandatoryLists[typeList].length == 0) {
            this.socket.on(typeList, (msg) => {

                let returnNode = this.applyAll(this.mandatoryLists[typeList], msg);

                if (msg && msg.callid) {
                    let callbackFunction = this.callMapping[msg.callid];
                    this.callMapping[msg.callid] = null;
                    if (callbackFunction) {
                        callbackFunction(msg, returnNode);
                    }
                }
            });
        }

        this.mandatoryLists[typeList].push(callback);
    }

    applyAll(functionList, msg) {
        let returnValue;
        for (let f of functionList) {
            if (f) {
                let nodeResult = f(msg);
                if (nodeResult) {
                    returnValue = nodeResult;
                }
            }
        }
        return returnValue;
    }

}

