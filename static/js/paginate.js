// Constants

const previousLink = document.getElementById('previous-link');
const nextLink = document.getElementById('next-link');

// Event Listeners

document.addEventListener('keydown', ev => {
    // Ignore within text input
    if (ev.target.nodeName === 'INPUT') {
        return;
    }

    if (ev.code === 'KeyU') {
        previousLink.click();
    }
    else if (ev.code === 'Space') {
        nextLink.click();
        ev.preventDefault();
    }
});
