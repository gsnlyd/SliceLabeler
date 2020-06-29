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

const sliceImg = document.getElementById('slice-img');

const minIntensityEl = document.getElementById('intensity-min');
const maxIntensityEl = document.getElementById('intensity-max');

const labelButtons = document.querySelectorAll('.viewer-label-button');

const previousLink = document.getElementById('previous-link');
const nextLink = document.getElementById('next-link');

// Slice Functions

function buildSliceURL(imageName, sliceType, sliceIndex, minInensity, maxIntensity) {
    return '/thumb/' + datasetName + '/' + imageName + '?slice_index=' +
        sliceIndex.toString() + '&slice_type=' + sliceType +
        '&min=' + Math.floor(minInensity) +
        '&max=' + Math.floor(maxIntensity);
}

function updateSlice() {
    sliceImg.src = buildSliceURL(imageName, sliceType, sliceIndex, minIntensityEl.value, maxIntensityEl.value);
}

// Labeling

async function setLabel(labelValue) {
    trackInteraction();
    const setLabelJson = {
        'label_session_id': labelSessionId,
        'image_slice_index': imageSliceIndex,
        'label_value': labelValue,
        'interaction_ms': interactionMs
    };
    const rawResponse = await fetch('/api/set-categorical-slice-label-value', {
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

for (const el of document.querySelectorAll('.viewer-number-input')) {
    el.addEventListener('change', ev => {
        updateSlice();
    });
}

for (const el of labelButtons) {
    el.addEventListener('click', ev => {
        setLabel(el.dataset.labelValue);
    });
}

document.addEventListener('keydown', ev => {
    if (ev.target.nodeName === 'INPUT') {
        return;
    }
    
    if (ev.code === 'KeyE') {
        maxIntensityEl.value = maxIntensityEl.value * 2;
        updateSlice();
    }
    else if (ev.code === 'KeyR') {
        maxIntensityEl.value = maxIntensityEl.value / 2;
        updateSlice();
    }
    else if (ev.code === 'Space') {
        nextLink.click();
    }
    else if (ev.code === 'KeyU') {
        previousLink.click();
    }
    else if (ev.code.startsWith('Digit')) {
        const num = parseInt(ev.code.substring(5, 6)) - 1;
        if (num >= 0 && num < labelButtons.length) {
            labelButtons[num].click();
        }
    }
});

// Run on page load

updateSlice();
