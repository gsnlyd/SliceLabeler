// Interaction Tracking

let lastInteraction = Date.now();
let interactionMs = 0;

const INTERACTION_SECONDS_BETWEEN = 15;

function trackInteraction() {
    const msElapsed = Date.now() - lastInteraction;
    if (msElapsed <= (INTERACTION_SECONDS_BETWEEN * 1000)) {
        interactionMs += msElapsed;
    }
    lastInteraction = Date.now();
}

function resetInteraction() {
    lastInteraction = Date.now();
    interactionMs = 0;
}

document.addEventListener('click', ev => {
    trackInteraction();
});

document.addEventListener('keydown', ev => {
    trackInteraction();
});

// Constants

const labelButtons = document.querySelectorAll('.viewer-label-button');

// Label Functions

function setImage(newImageIndex) {
    const paramString = new URLSearchParams({
        'label_session': labelSessionId,
        'i': newImageIndex
    }).toString();
    window.location = '/label?' + paramString;
}

async function setLabel(labelValue) {
    trackInteraction();
    const setLabelJson = {
        'element_id': elementId,
        'label_value': labelValue,
        'ms': interactionMs
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

    for (const buttonEl of labelButtons) {
        if (buttonEl.dataset.labelValue === labelValue) {
            buttonEl.classList.add('selected');
        }
        else {
            buttonEl.classList.remove('selected');
        }
    }
    resetInteraction();
}

// Event Listeners

document.addEventListener('keydown', ev => {
    // Ignore within text input
    if (ev.target.nodeName === 'INPUT') {
        return;
    }

    // Previous Image
    if (ev.code === 'KeyU') {
        setImage(Math.max(0, imageIndex - 1));
    }
    // Next Image
    else if (ev.code === 'Space') {
        setImage(Math.min(imageCount - 1, imageIndex + 1));

        ev.preventDefault();
    }
    // Label
    else if (ev.code.startsWith('Digit')) {
        const num = parseInt(ev.code.substring(5, 6)) - 1;
        if (num >= 0 && num < labelButtons.length) {
            labelButtons[num].click();
        }
    }
});

for (const buttonEl of labelButtons) {
    buttonEl.addEventListener('click', ev => {
        setLabel(buttonEl.dataset.labelValue)
    })
}
