/**
 * TabGenerator is a class that generates the general layout of the webpage 
 * and handles the different tabs that can be opened
 * @constructor
 * @public
 */

export default class TabGenerator {

    constructor(container) {
        /**
         * 
         */
        this.container = container;
        this.containerList = []
        this.list = document.createElement('ul');
        this.list.classList.add('tabs');
        this.container.appendChild(this.list);

    }
/**
 * generateTab creates a new tab and returns its HTML element
 * @param {String} title The name of the tab
 * @param {Boolean} selected Put this to true on the tab that should be oopen at the start
 * @returns 
 */
    generateTab(title, selected = false) {
        let nr = this.containerList.length;

        let listItem = document.createElement('li');
        listItem.setAttribute('role', 'tab');
        this.list.appendChild(listItem);

        let input = document.createElement('input');
        input.setAttribute('type', 'radio');
        input.setAttribute('name', 'tabs');
        input.setAttribute('id', 'tab' + nr);
        if (selected) {
            input.setAttribute('checked', 'true');
        }

        input.onchange = () => {
            let event = new CustomEvent(
                'tabOpened',
                {
                    detail: {
                        title: title,
                    },
                    bubbles: true,
                    cancelable: true
                }
            );
            let serverDiv = document.getElementById('connectedServer');
            serverDiv.dispatchEvent(event);
        }

        listItem.appendChild(input);

        let label = document.createElement('label');
        label.setAttribute('for', 'tab' + nr);
        label.setAttribute('role', 'tabs');
        label.setAttribute('aria-selected', 'false');
        label.setAttribute('aria-controls', 'panel' + nr);
        label.setAttribute('tab-index', nr);
        label.innerText = title;
        listItem.appendChild(label);

        let contentDiv = document.createElement('div');
        contentDiv.classList.add('tab-content');
        contentDiv.setAttribute('id', 'tab-content' + nr);
        contentDiv.classList.add('tab-content');
        contentDiv.setAttribute('role', 'tab-panel');
        contentDiv.setAttribute('aria-labeledby', 'specification');
        contentDiv.setAttribute('aria-hidden', 'true');
        listItem.appendChild(contentDiv);
        this.containerList.push(contentDiv);

        return contentDiv;
    }
/**
 * displayError is a general way of generating a pop-up window to notify the user
 * when something has happened with the communication chain
 * @param {*} message The error message
 * @param {*} context The context of the error, for example the name of the OPC UA call that failed
 */
    displayError(message, context) { 
        let contentDiv = document.createElement('div');
        contentDiv.classList.add('errorTab');
        this.container.appendChild(contentDiv);
        let titleDiv = document.createElement('div');
        let innerDiv = document.createElement('div');
        titleDiv.innerText=`OPC UA communication failure in ${context} function`
        innerDiv.innerText=`${message}`;
        
        contentDiv.appendChild(titleDiv);
        contentDiv.appendChild(innerDiv);
        window.setTimeout(()=>{
            this.container.removeChild(contentDiv);
        }, 15000)
    }
}
