// Constants

const slice1 = document.getElementById('slice-1');
const slice2 = document.getElementById('slice-2');

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

// Event Listeners

for (const el of document.querySelectorAll('.viewer-number-input')) {
    el.addEventListener('change', ev => {
        updateSlices();
    });
}

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
});

// Run on page load

updateSlices();
