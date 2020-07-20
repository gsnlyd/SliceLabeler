// Constants

const sliceTypeNames = ['SAGITTAL', 'CORONAL', 'AXIAL'];

const sliceTypeSelect = document.getElementById('slice-type-select');

const sliceSideElements = [
    document.getElementById('slice-side-1'),
    document.getElementById('slice-side-2'),
    document.getElementById('slice-side-3')
];

const sliceMainElement = document.getElementById('slice-main');

const guideElements = [
    document.getElementById('slice-guide-1'),
    document.getElementById('slice-guide-2'),
    document.getElementById('slice-guide-3')
];

const currentSliceIndicator = document.getElementById('current-slice');

// Viewer Functions

function updateSlices() {
    const curTypeIndex = sliceTypeSelect.selectedIndex;
    let isHorizontal;
    if (curTypeIndex === 0) {
        isHorizontal = [null, false, false];
    }
    else if (curTypeIndex === 1) {
        isHorizontal = [false, null, true];
    }
    else {
        isHorizontal = [true, true, null];
    }

    const positionPercent = (sliceIndices[curTypeIndex] / sliceCounts[curTypeIndex]) * 100;

    for (let i = 0; i < sliceTypeNames.length; i++) {
        const el = sliceSideElements[i];
        setSliceOptions(el, sliceTypeNames[i], sliceIndices[i]);

        if (i === curTypeIndex) {
            el.parentElement.parentElement.classList.add('selected');
        }
        else {
            const guide = guideElements[i];
            if (isHorizontal[i]) {
                guide.style.top = (100 - positionPercent).toString() + '%';
                guide.style.left = '0';

                guide.classList.add('horizontal');
                guide.parentElement.classList.add('horizontal');
            }
            else {
                guide.style.top = '0';
                guide.style.left = positionPercent.toString() + '%';

                guide.classList.remove('horizontal');
                guide.parentElement.classList.remove('horizontal');
            }
            el.parentElement.parentElement.classList.remove('selected');
        }
    }
    setSliceOptions(sliceMainElement, sliceTypeNames[curTypeIndex], sliceIndices[curTypeIndex]);

    currentSliceIndicator.textContent = (sliceIndices[curTypeIndex] + 1).toString() + ' / ' + sliceCounts[curTypeIndex].toString();
}

function setSliceType(sliceTypeIndex) {
    sliceTypeIndex = Math.max(0, Math.min(sliceTypeIndex, sliceTypeNames.length - 1));
    sliceTypeSelect.selectedIndex = sliceTypeIndex;

    updateSlices();
}

// Event Listeners

document.addEventListener('keydown', ev => {
    if (ev.target.nodeName === 'INPUT') {
        return;
    }

    let amount;

    if (ev.getModifierState('Shift')) {
        amount = 10;
    }
    else {
        amount = 1;
    }

    const curTypeIndex = sliceTypeSelect.value;

    if (ev.code === 'ArrowLeft' || ev.code === 'KeyA') {
        sliceIndices[curTypeIndex] = Math.max(0, sliceIndices[curTypeIndex] - amount);
        updateSlices();
    }
    else if (ev.code === 'ArrowRight' || ev.code === 'KeyD') {
        sliceIndices[curTypeIndex] = Math.min(sliceCounts[curTypeIndex] - 1, sliceIndices[curTypeIndex] + amount);
        updateSlices();
    }
    else if (ev.code === 'ArrowUp' || ev.code === 'KeyW') {
        setSliceType(curTypeIndex - 1);
        ev.preventDefault();
    }
    else if (ev.code === 'ArrowDown' || ev.code === 'KeyS') {
        setSliceType(curTypeIndex + 1);
        ev.preventDefault();
    }
});

sliceTypeSelect.addEventListener('change', ev => {
    setSliceType(sliceTypeSelect.selectedIndex);
    updateSlices();
});

// Run on page load

updateSlices();
