// Constants

const sliceImg = document.getElementById('slice-img');

const minIntensityEl = document.getElementById('intensity-min');
const maxIntensityEl = document.getElementById('intensity-max');

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

// Event Listeners

for (const el of document.querySelectorAll('.viewer-number-input')) {
    el.addEventListener('change', ev => {
        updateSlice();
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
});

// Run on page load

updateSlice();
