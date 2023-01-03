

export default class ModelToHTML {

    constructor(messageArea) {
        this.messageArea = messageArea;
        this.longVersionOuter; // This contains the HTML representation in detail
        this.shortVersion; // This contains the HTML representation in brief
    }

    toHTML(model, brief = true, parentName) {
        function toggler(shortVersion, longVersionOuter) {

            // Eventhandlers to handle expanding or shrinking the HTML representation 
            // of a complex value
            longVersionOuter.addEventListener("click", (e) => {
                if (!e) var e = window.event;
                e.cancelBubble = true;
                if (e.stopPropagation) e.stopPropagation();
                longVersionOuter.style.display = 'none';
                shortVersion.style.display = 'block';
            }, false);
            shortVersion.addEventListener("click", (e) => {
                if (!e) var e = window.event;
                e.cancelBubble = true;
                if (e.stopPropagation) e.stopPropagation();
                longVersionOuter.style.display = 'block';
                shortVersion.style.display = 'none';
            }, false);
        }

        // Seting up the HTML containers for expanded or shrunken complex value
        let combined = document.createElement('li');
        let shortVersion = document.createElement('li');
        let longVersionOuter = document.createElement('li');
        longVersionOuter.style.display = 'none';
        let longVersion = document.createElement('li');
        longVersion.classList.add('indent');

        if (parentName) {
            let ownerName = document.createElement('li');
            let ownerName2 = document.createElement('li');
            ownerName.innerHTML = parentName + '&#9655;';
            ownerName2.innerHTML = parentName + '&#9661;';
            shortVersion.appendChild(ownerName);
            longVersionOuter.appendChild(ownerName2);
        }

        // Tie the eventhandlers to the expanded or shrunken complex value
        toggler(shortVersion, longVersionOuter);

        // combine the expanded or shrunken complex value
        combined.appendChild(shortVersion);
        longVersionOuter.appendChild(longVersion);
        combined.appendChild(longVersionOuter);
        combined.longVersionOuter = longVersionOuter
        combined.shortVersion = shortVersion;
        combined.expandLong = function () { // This is used to get the initial display expanded
            if (this.longVersionOuter && this.shortVersion) {
                this.longVersionOuter.style.display = 'block';
                this.shortVersion.style.display = 'none';
            }
        }

        // Loop over the model object and handle diffrent types of values 
        // such as arrays, nesting
        for (const [key, value] of Object.entries(model)) {
            //console.log(`${key}: ${value}`);

            if (Array == value.constructor) {
                // Handle an array of values (that may be complex values)
                var outerList = document.createElement('li');
                longVersion.appendChild(outerList);
                let ownerName = document.createElement('li');
                ownerName.innerHTML = key + '(' + value.length + ') &#9655;';
                outerList.appendChild(ownerName);

                var item = document.createElement('li');
                var ind = document.createElement('li');
                item.style.display = 'none';
                let ownerName2 = document.createElement('li');
                ownerName2.innerHTML = key + '&#9661;';
                ind.classList.add('indent');
                item.appendChild(ownerName2);
                item.appendChild(ind);
                outerList.appendChild(item);

                toggler(ownerName, item);

                let i = 0;
                for (let v of value) {
                    if ('object' == typeof v) {
                        let obj = this.toHTML(v, brief, '[' + i + ']');
                        ind.appendChild(obj);
                    } else {
                        let li = document.createElement('li');
                        li.innerHTML = v;
                        ind.appendChild(li);
                    }
                    i++;
                }
            } else if ('object' == typeof value && key != 'debugValues' && value.type != 'linkedValue') {
                // Here recursion is used to handle nested complex values
                let item = this.toHTML(value, brief, key);
                //let item = value.toHTML(brief, key);
                longVersion.appendChild(item);
            } else if ('object' == typeof value && key != 'debugValues' && value.type == 'linkedValue') {
                // Here linked objects are displayed
                var item = document.createElement('li');
                item.textContent = `${key}: ${value.value} LINKED*****************************************`;
                longVersion.appendChild(item);
                item.onclick = () => {
                    value.link.display(messages)
                };
            }
            else if (key != 'debugValues') {
                // This handles the most simple type of name-value pair
                var item = document.createElement('li');
                item.textContent = `${key}: ${value}`;
                longVersion.appendChild(item);
            }
        }
        if (shortVersion.innerHTML == '') {
            shortVersion.appendChild(longVersion.children[0].cloneNode());
        }
        return combined;
    }

    display(model) {
        let onScreen;
        if ('object' == typeof model) {       // Handle a model
            let onScreen;
            onScreen = this.toHTML(model, true, 'Response');
            onScreen.expandLong();
            //var item = document.createElement('li');
            //item.textContent = `${msg.dataValue.serverTimestamp}`;
            //messages.appendChild(item);

            this.messageArea.appendChild(onScreen);
            this.messageArea.scrollTo(0, this.messageArea.scrollHeight);
            onScreen.scrollIntoView();
        } else {                              // Handle a single value
            onScreen = document.createElement('li');
            onScreen.innerHTML = model;
            this.messageArea.appendChild(onScreen);
            this.messageArea.scrollTo(0, this.messageArea.scrollHeight);
            onScreen.scrollIntoView();
        }
    }
}