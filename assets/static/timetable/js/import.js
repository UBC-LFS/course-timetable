(function () {
  const root = document.getElementById('import-root');
  if (!root) return;

  const populatePreviewUrl = root.dataset.populatePreviewUrl;
  const populateCommitUrl = root.dataset.populateCommitUrl;
  const importPageUrl = root.dataset.importPageUrl;

  const form = document.getElementById('importUploadForm');
  const fileInput = document.getElementById('fileInput');
  const dropZone = document.getElementById('dropZone');
  const dzSubDefault = document.getElementById('dz-sub-default');
  const dzSubMeta = document.getElementById('dz-sub-meta');
  const fileNameEl = document.getElementById('fileName');
  const fileSizeEl = document.getElementById('fileSize');
  const fileClearBtn = document.getElementById('fileClearBtn');
  const populateBtn = document.getElementById('populateBtn');
  const csrfTokenEl = document.querySelector('input[name=csrfmiddlewaretoken]');
  const csrfToken = csrfTokenEl ? csrfTokenEl.value : '';

  // initial state from server
  let uploadSuccess = root.dataset.uploadSuccess === 'true';
  let isUploading = false;

  function setInitialStateFromServer() {
    if (uploadSuccess) {
      if (fileInput) fileInput.disabled = true;
      if (populateBtn) populateBtn.disabled = false;
    } else {
      if (fileInput) fileInput.disabled = false;
      if (populateBtn) populateBtn.disabled = true;
    }
    isUploading = false;
  }

  if (dropZone && fileInput && form && dzSubDefault && dzSubMeta) {
    // on click, open file dialog
    dropZone.addEventListener('click', function () {
      if (uploadSuccess || isUploading) return;
      fileInput.click();
    });

    // when user chooses a file, submit the form (standard POST)
    fileInput.addEventListener('change', function (e) {
      if (!e.target.files.length) return;
      // show "Uploading..." in the drop area until the page reloads
      isUploading = true;
      dzSubDefault.classList.remove('d-none');
      dzSubMeta.classList.add('d-none');
      dzSubDefault.textContent = 'Uploading...';
      form.submit();
    });

    // drag & drop behaviour (still uses normal POST once a file is dropped)
    ['dragenter', 'dragover'].forEach(function (ev) {
      dropZone.addEventListener(ev, function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (uploadSuccess || isUploading) return;
        dropZone.classList.add('drop-hover');
      });
    });

    ['dragleave', 'drop'].forEach(function (ev) {
      dropZone.addEventListener(ev, function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('drop-hover');
      });
    });

    dropZone.addEventListener('drop', function (e) {
      if (uploadSuccess || isUploading) return;
      const dt = e.dataTransfer;
      if (!dt || !dt.files.length) return;

      const file = dt.files[0]; // enforce single file
      const dataTransferInput = fileInput;

      // put dropped file onto the hidden input, then submit
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      dataTransferInput.files = dataTransfer.files;

      isUploading = true;
      dzSubDefault.classList.remove('d-none');
      dzSubMeta.classList.add('d-none');
      dzSubDefault.textContent = 'Uploading...';
      form.submit();
    });
  }

  // X button: reset
  if (fileClearBtn && fileInput && dzSubDefault && dzSubMeta && populateBtn) {
    fileClearBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      uploadSuccess = false;
      fileInput.disabled = false;
      isUploading = false;
      fileInput.value = '';
      dzSubDefault.textContent = 'You can upload 1 file';
      dzSubDefault.classList.remove('d-none');
      dzSubMeta.classList.add('d-none');
      populateBtn.disabled = true;
    });
  }

  // Populate
  const progressModalEl = document.getElementById('populateProgressModal');
  const courseFieldsModalEl = document.getElementById('courseFieldsModal');
  const coursesModalEl = document.getElementById('coursesModal');
  const commitModalEl = document.getElementById('populateCommitModal');

  if (!progressModalEl || !courseFieldsModalEl || !coursesModalEl || !commitModalEl) {
    setInitialStateFromServer();
    return;
  }

  const progressModal = new bootstrap.Modal(progressModalEl);
  const courseFieldsModal = new bootstrap.Modal(courseFieldsModalEl);
  const coursesModal = new bootstrap.Modal(coursesModalEl);
  const commitModal = new bootstrap.Modal(commitModalEl);

  const fieldCodesEl = document.getElementById('fieldCodes');
  const fieldNumbersEl = document.getElementById('fieldNumbers');
  const fieldSectionsEl = document.getElementById('fieldSections');
  const fieldYearsEl = document.getElementById('fieldYears');
  const fieldTermsEl = document.getElementById('fieldTerms');
  const fieldDaysEl = document.getElementById('fieldDays');
  const fieldTimesEl = document.getElementById('fieldTimes');
  const coursesListEl = document.getElementById('coursesList');

  const courseFieldsConfirmBtn = document.getElementById('courseFieldsConfirm');
  const coursesConfirmBtn = document.getElementById('coursesConfirm');

  function listOrNone(arr) {
    if (!arr || arr.length === 0) {
      return 'None';
    }
    return arr.join(', ');
  }

  // flags to distinguish Confirm to close modal vs. dismiss ("X" on top right or places outside modal) to close modal
  let fieldsConfirmed = false;
  let coursesConfirmed = false;

  // If user closes Created Course Fields modal via X / outside, reset to initial state
  courseFieldsModalEl.addEventListener('hidden.bs.modal', function () {
    if (!fieldsConfirmed) {
      window.location.href = importPageUrl;
    }
  });

  // If user closes Created Courses modal via X / outside, reset to initial state
  coursesModalEl.addEventListener('hidden.bs.modal', function () {
    if (!coursesConfirmed) {
      window.location.href = importPageUrl;
    }
  });

  if (populateBtn) {
    populateBtn.addEventListener('click', function () {
      if (!uploadSuccess) {
        return;
      }

      // Reset flags at the start of each populate run
      fieldsConfirmed = false;
      coursesConfirmed = false;

      // Show blocking progress modal
      progressModal.show();

      fetch(populatePreviewUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
        .then((response) => response.json())
        .then((data) => {
          progressModal.hide();

          if (!data.ok) {
            if (data.redirect) {
              window.location.href = data.redirect;
            } else {
              window.location.reload();
            }
            return;
          }

          const fields = data.course_fields || {};

          // course fields preview
          if (fieldCodesEl) fieldCodesEl.textContent = listOrNone(fields.codes);
          if (fieldNumbersEl) fieldNumbersEl.textContent = listOrNone(fields.numbers);
          if (fieldSectionsEl) fieldSectionsEl.textContent = listOrNone(fields.sections);
          if (fieldYearsEl) fieldYearsEl.textContent = listOrNone(fields.years);
          if (fieldTermsEl) fieldTermsEl.textContent = listOrNone(fields.terms);
          if (fieldDaysEl) fieldDaysEl.textContent = listOrNone(fields.days);
          if (fieldTimesEl) fieldTimesEl.textContent = listOrNone(fields.times);

          // Courses preview
          if (coursesListEl) {
            coursesListEl.innerHTML = '';
            const courses = data.courses || [];
            if (courses.length === 0) {
              const li = document.createElement('li');
              li.textContent = 'No courses will be created';
              coursesListEl.appendChild(li);
            } else {
              courses.forEach((c) => {
                const li = document.createElement('li');
                const code = c.code || 'None';
                const number = c.number || 'None';
                const section = c.section || 'None';
                const year = c.year || 'None';
                const term = c.term || 'None';
                li.textContent = `${code} ${number} ${section} ${year} ${term}`;
                coursesListEl.appendChild(li);
              });
            }
          }

          courseFieldsModal.show();
        })
        .catch(() => {
          // fallback
          progressModal.hide();
          window.location.reload();
        });
    });
  }

  if (courseFieldsConfirmBtn && coursesConfirmBtn) {
    // When user confirms created fields, show courses modal
    courseFieldsConfirmBtn.addEventListener('click', function () {
      fieldsConfirmed = true;
      courseFieldsModal.hide();
      coursesModal.show();
    });

    // When user confirms courses, actually commit to DB
    coursesConfirmBtn.addEventListener('click', function () {
      coursesConfirmed = true;
      coursesConfirmBtn.disabled = true;

      coursesModal.hide();
      commitModal.show();

      fetch(populateCommitUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
        .then((response) => response.json())
        .then((data) => {
          commitModal.hide();
          if (data.redirect) {
            window.location.href = data.redirect;
          } else {
            window.location.reload();
          }
        })
        .catch(() => {
          // fallback
          commitModal.hide();
          window.location.reload();
        });
    });
  }

  setInitialStateFromServer();
})();
