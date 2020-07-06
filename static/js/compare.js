// Time Tracking

let startTime = Date.now();

function getTimeTaken() {
    return Date.now() - startTime;
}

function resetTimeTaken() {
    startTime = Date.now();
}

// Constants

const slice1 = document.getElementById('slice-1');
const slice2 = document.getElementById('slice-2');

const neitherButton = document.getElementById('neither-button');
const notSureButton = document.getElementById('not-sure-button');

const minIntensityEl1 = document.getElementById('intensity-min-1');
const maxIntensityEl1 = document.getElementById('intensity-max-1');

const minIntensityEl2 = document.getElementById('intensity-min-2');
const maxIntensityEl2 = document.getElementById('intensity-max-2');

// Compare Functions

function buildSliceURL(imageName, sliceType, sliceIndex, minInensity, maxIntensity) {
    return '/thumb/' + datasetName + '/' + imageName + '?slice_index=' +
        sliceIndex.toString() + '&slice_type=' + sliceType +
        '&min=' + Math.floor(minInensity) +
        '&max=' + Math.floor(maxIntensity);
}

function updateSlices() {
    slice1.src = buildSliceURL(imageName1, sliceType1, sliceIndex1, minIntensityEl1.value, maxIntensityEl1.value);
    slice2.src = buildSliceURL(imageName2, sliceType2, sliceIndex2, minIntensityEl2.value, maxIntensityEl2.value);
}

function updateSelected(labelValue) {
    slice1.classList.remove('selected');
    slice2.classList.remove('selected');
    neitherButton.classList.remove('selected');
    notSureButton.classList.remove('selected');

    if (labelValue === 'First') {
        slice1.classList.add('selected');
    }
    else if (labelValue === 'Second') {
        slice2.classList.add('selected');
    }
    else if (labelValue === 'Neither') {
        neitherButton.classList.add('selected');
    }
    else if (labelValue === 'Not Sure') {
        notSureButton.classList.add('selected');
    }
}

async function setLabel(labelValue) {
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

    updateSelected(labelValue);
    resetTimeTaken();
}

// Event Listeners

for (const el of document.querySelectorAll('.viewer-number-input')) {
    el.addEventListener('change', ev => {
        updateSlices();
    });
}

slice1.addEventListener('click', ev => {
    setLabel('First');
});

slice2.addEventListener('click', ev => {
    setLabel('Second');
});

neitherButton.addEventListener('click', ev => {
    setLabel('Neither');
});

notSureButton.addEventListener('click', ev => {
    setLabel('Not Sure');
});

document.addEventListener('keydown', ev => {
    if (ev.target.nodeName === 'INPUT') {
        return;
    }

    if (ev.code === 'KeyE') {
        maxIntensityEl1.value = maxIntensityEl1.value * 2;
        maxIntensityEl2.value = maxIntensityEl2.value * 2;
        updateSlices();
    }
    else if (ev.code === 'KeyR') {
        maxIntensityEl1.value = maxIntensityEl1.value / 2;
        maxIntensityEl2.value = maxIntensityEl2.value / 2;
        updateSlices();
    }
    else if(ev.code === 'Digit1') {
        setLabel('First');
    }
    else if(ev.code === 'Digit2') {
        setLabel('Second');
    }
    else if(ev.code === 'Digit3') {
        setLabel('Neither');
    }
    else if(ev.code === 'Digit4') {
        setLabel('Not Sure');
    }
});

// Run on page load

updateSlices();
updateSelected(initialLabel);
