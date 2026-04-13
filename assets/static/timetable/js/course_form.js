// display correct options to user
(function () {

    function activateCorrectMode(element) {

        const form = document.querySelector('form');
        const regularOptions = form.querySelector('div#regular-options');
        const offCycleOptions = form.querySelector('div#off-cycle-options');

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

    const offCycleCheckbox = document.querySelector('input#id_off_cycle');
    activateCorrectMode(offCycleCheckbox);

    offCycleCheckbox.addEventListener('click', function (event) {
        activateCorrectMode(event.currentTarget);
    });
})();

// clear out forms 
(function () {

    const form = document.querySelector('form');

    form.addEventListener('submit', function (event) {
        // for debugging
        event.preventDefault();

        const offCycleCheckbox = document.querySelector('input#id_off_cycle');
        if(offCycleCheckbox.checked) {
            const regularOptions = event.currentTarget.querySelector('div#regular-options');
            const checkboxes = regularOptions.querySelectorAll('input[type="checkbox"]');
            const selects =  regularOptions.querySelectorAll('select');

            for(const checkbox of checkboxes) {
                checkbox.checked = false;
            }

            for(const select of selects) {
                select.value = '';
            }
        } else {
            const offCycleOptions = event.currentTarget.querySelector('div#off-cycle-options');
            const checkboxes = offCycleOptions.querySelectorAll('input[type="checkbox"]');
            const selects = offCycleOptions.querySelectorAll('select');

            for(const checkbox of checkboxes) {
                checkbox.checked = false;
            }

            for(const select of selects) {
                select.value = '';
            }
        }
    });
})();