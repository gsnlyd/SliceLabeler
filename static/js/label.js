// Time Tracking

let startTime = Date.now();

function getTimeTaken() {
    return Date.now() - startTime;
}

function resetTimeTaken() {
    startTime = Date.now();
}

// Constants

let labelControls = {};
for (const controlEl of document.querySelectorAll('.label-control')) {
    labelControls[controlEl.dataset.controlIndex] = controlEl;
}

// Label Functions

async function setLabel(elementId, labelValue) {
    const setLabelJson = {
        'element_id': elementId,
        'label_value': labelValue,
        'ms': getTimeTaken()
    };
    const rawResponse = await fetch('/api/set-label-value', {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(setLabelJson)
    });

    if (!rawResponse.ok) {
        console.log('Label failed');
        return;
    }
    console.log('Label succeeded');

    for (const controlEl of Object.values(labelControls)) {
        controlEl.classList.toggle('selected', controlEl.dataset.labelValue === labelValue)
    }

    resetTimeTaken();
}

// Event Listeners

document.addEventListener('keydown', ev => {
    // Ignore within text input
    if (ev.target.nodeName === 'INPUT') {
        return;
    }

    // Label
    if (ev.code.startsWith('Digit')) {
        const numString = (parseInt(ev.code.substring(5, 6)) - 1).toString();
        if (Object.keys(labelControls).includes(numString)) {
            labelControls[numString].click();
        }
    }
});

for (const controlEl of Object.values(labelControls)) {
    controlEl.addEventListener('click', ev => {
        setLabel(controlEl.dataset.elementId, controlEl.dataset.labelValue);
    })
}
