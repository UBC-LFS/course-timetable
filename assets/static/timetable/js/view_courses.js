(function () {
  const $term = $('#courses-term');
  if ($term.hasClass('select2-hidden-accessible')) {
    $term.select2('destroy');
  }
  $term.select2({
    placeholder: "Select Terms",
    width: '100%',
    allowClear: true
  });

  const $year = $('#courses-year');
  if ($year.hasClass('select2-hidden-accessible')) {
    $year.select2('destroy');
  }
  $year.select2({
    placeholder: "Select Years",
    width: '100%',
    allowClear: true
  });

  const $day = $('#courses-day');
  if ($day.hasClass('select2-hidden-accessible')) {
    $day.select2('destroy');
  }
  $day.select2({
    placeholder: "Select Days",
    width: '100%',
    allowClear: true
  });

  // Clear button
  const clearBtn = document.getElementById('clear-filters');
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      // Clear multi-selects (Year, Term, Day)
      $year.val(null).trigger('change');
      $term.val(null).trigger('change');
      $day.val(null).trigger('change');

      // Clear text inputs (Code, Number, Section)
      $('input[name="code"]').val('');
      $('input[name="number"]').val('');
      $('input[name="section"]').val('');
    });
  }
})();
