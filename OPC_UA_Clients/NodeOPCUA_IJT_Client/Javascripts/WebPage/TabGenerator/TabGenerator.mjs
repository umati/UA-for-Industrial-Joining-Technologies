

export default class TabGenerator {

    constructor(container) {
        this.container = container;
        this.containerList = []
        this.list = document.createElement('ul');
        this.list.classList.add("tabs");
        this.container.appendChild(this.list);

    }

    generateTab(title, selected = false) {
        let nr = this.containerList.length;

        let listItem = document.createElement('li');
        listItem.setAttribute("role", "tab");
        this.list.appendChild(listItem);

        let input = document.createElement('input');
        input.setAttribute("type", "radio");
        input.setAttribute("name", "tabs");
        input.setAttribute("id", "tab" + nr);
        if (selected) {
            input.setAttribute("checked", "true");
        }

        input.onchange = () => {
            let event = new CustomEvent(
                "tabOpened",
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
        label.setAttribute("for", "tab" + nr);
        label.setAttribute("role", "tabs");
        label.setAttribute("aria-selected", "false");
        label.setAttribute("aria-controls", "panel" + nr);
        label.setAttribute("tab-index", nr);
        label.innerText = title;
        listItem.appendChild(label);

        let contentDiv = document.createElement('div');
        contentDiv.classList.add("tab-content");
        contentDiv.setAttribute("id", "tab-content" + nr);
        contentDiv.classList.add("tab-content");
        contentDiv.setAttribute("role", "tab-panel");
        contentDiv.setAttribute("aria-labeledby", "specification");
        contentDiv.setAttribute("aria-hidden", "true");
        listItem.appendChild(contentDiv);
        this.containerList.push(contentDiv);

        return contentDiv;
    }

}
