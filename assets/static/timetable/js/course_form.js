(function () {

    function activateCorrectMode(element) {

        const regularOptions = document.getElementById('regular-options');
        const offCycleOptions = document.getElementById('off-cycle-options');

        if(element.checked) {
            regularOptions.style.display = 'none';
            regularOptions.disabled = true;
            offCycleOptions.style.display = '';
            offCycleOptions.disabled = false;
        } else {
            regularOptions.style.display = '';
            regularOptions.disabled = false;
            offCycleOptions.style.display = 'none';
            offCycleOptions.disabled = true;
        }

    }

    const offCycleSelect = document.getElementById('id_off_cycle');
    activateCorrectMode(offCycleSelect);

    offCycleSelect.addEventListener('click', (e) => {
        console.log('Off cycle box clicked');
        console.log(e.target)
        activateCorrectMode(e.target);
    });
})();