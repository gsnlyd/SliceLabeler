// Cookies

function getCookie(key) {
    for (let c of document.cookie.split(';')) {
        c = c.trim();
        if (c.startsWith(key + '=')) {
            return c.substr(key.length + 1);
        }
    }
    return null
}

function setCookie(key, value, maxAge) {
    document.cookie = key + '=' + value + ';path=/;max-age=' + maxAge.toString() + ';';
}

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

const minIntensityControls = document.querySelectorAll('.intensity-control-min');
const maxIntensityControls = document.querySelectorAll('.intensity-control-max');

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

function updateSlice(sliceEl) {
    const datasetName = sliceEl.dataset.datasetName;
    const imageName = sliceEl.dataset.imageName;
    const queryParams = {
        'slice_index': sliceEl.dataset.sliceIndex,
        'slice_type': sliceEl.dataset.sliceType,
        'min': Math.floor(parseFloat(sliceEl.dataset.intensityMin)),
        'max': Math.floor(parseFloat(sliceEl.dataset.intensityMax))
    };

    sliceEl.src = '/thumb/' + datasetName + '/' + imageName + '?' + new URLSearchParams(queryParams).toString();
}

function setSliceOptions(sliceEl, sliceType, sliceIndex) {
    sliceEl.dataset.sliceType = sliceType;
    sliceEl.dataset.sliceIndex = sliceIndex.toString();
    updateSlice(sliceEl);
}

function setSliceIntensity(sliceEl, intensityMin, intensityMax) {
    if (intensityMin !== null) {
        sliceEl.dataset.intensityMin = intensityMin;
    }
    if (intensityMax !== null) {
        sliceEl.dataset.intensityMax = intensityMax;
    }
    updateSlice(sliceEl);
}

function getTargets(controlEl) {
    let targetElements = [];
    for (const targetId of controlEl.dataset.forSlice.split(',')) {
        targetElements.push(document.getElementById(targetId));
    }
    return targetElements;
}

function updateMinEl(intensityEl) {
    for (const targetEl of getTargets(intensityEl)) {
        setSliceIntensity(targetEl, intensityEl.value, null);
    }
}

function updateMaxEl(intensityEl) {
    for (const targetEl of getTargets(intensityEl)) {
        setSliceIntensity(targetEl, null, intensityEl.value);
    }
}

const INTENSITY_MULTIPLIER_KEY = 'intensityMultiplier';
const INTENSITY_MULTIPLIER_MAX_AGE = 86400; // 1 day

const multiplierInfoEl = document.getElementById('multiplier-info');

function updateMultiplierInfo() {
    multiplierInfoEl.textContent = 'x' + getCurMultiplier().toString();
}

function getCurMultiplier() {
    const curMultiplier = getCookie(INTENSITY_MULTIPLIER_KEY);
    if (curMultiplier === null) {
        return 1;
    }
    return curMultiplier;
}

function initMultiplier() {
    const curMultiplier = getCurMultiplier();
    for (const maxEl of maxIntensityControls) {
        maxEl.value = maxEl.value * curMultiplier;
        updateMaxEl(maxEl);
    }
    updateMultiplierInfo();
}

function changeIntensityMultiplier(up) {
    const curMultiplier = getCurMultiplier();
    const changeMultiplier = up ? 2 : 0.5;
    setCookie(INTENSITY_MULTIPLIER_KEY, curMultiplier * changeMultiplier, INTENSITY_MULTIPLIER_MAX_AGE);

    for (const maxEl of maxIntensityControls) {
        maxEl.value = maxEl.value * changeMultiplier;
        updateMaxEl(maxEl);
    }
    updateMultiplierInfo();
}

// Event Listeners

document.addEventListener('keydown', ev => {
    // Ignore within text input
    if (ev.target.nodeName === 'INPUT') {
        return;
    }

    // Ignore keyboard commands
    if (ev.getModifierState('Alt') || ev.getModifierState('Control') || ev.getModifierState('Meta')) {
        return;
    }

    // Label
    if (ev.code.startsWith('Digit')) {
        const numString = (parseInt(ev.code.substring(5, 6)) - 1).toString();
        if (Object.keys(labelControls).includes(numString)) {
            labelControls[numString].click();
        }
    }
    else if (ev.code === 'KeyE') {
        changeIntensityMultiplier(true);
    }
    else if (ev.code === 'KeyR') {
        changeIntensityMultiplier(false);
    }
});

for (const controlEl of Object.values(labelControls)) {
    controlEl.addEventListener('click', ev => {
        setLabel(controlEl.dataset.elementId, controlEl.dataset.labelValue);
    })
}

for (const intensityEl of minIntensityControls) {
    intensityEl.addEventListener('change', ev => {
        updateMinEl(intensityEl);
    });
}

for (const intensityEl of maxIntensityControls) {
    intensityEl.addEventListener('change', ev => {
        updateMaxEl(intensityEl);
    });
}

// Run on page load

for (const sliceEl of document.querySelectorAll('.slice-img')) {
    updateSlice(sliceEl);
}

initMultiplier();
