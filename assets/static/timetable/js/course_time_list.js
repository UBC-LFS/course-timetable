(function () {
  const root = document.getElementById('course-times-root');
  if (!root) return;

  const updateUrlTemplate = root.dataset.updateUrl;
  const deleteUrlTemplate = root.dataset.deleteUrl;
  const affectedUrlTemplate = root.dataset.affectedUrl;

  function buildUrl(template, id) {
    if (!template) return '';
    return template.replace('0', id);
  }

  // CREATE
  (function () {
    const form = document.querySelector('#createModal form');
    const hour = document.getElementById('createHour');
    const min = document.getElementById('createMinute');
    const hid = document.getElementById('createHiddenTime');
    if (form) {
      form.addEventListener('submit', function () {
        hid.value = `${hour.value}:${min.value}`;
      });
    }
  })();

  // EDIT
  (function () {
    const form = document.getElementById('editForm');
    const hour = document.getElementById('editHour');
    const min = document.getElementById('editMinute');
    const hid = document.getElementById('editHiddenTime');
    if (form) {
      form.addEventListener('submit', function () {
        hid.value = `${hour.value}:${min.value}`;
      });
    }
  })();

  const editModal = document.getElementById('editModal');
  if (editModal) {
    editModal.addEventListener('show.bs.modal', function (event) {
      const btn = event.relatedTarget;
      const id = btn.getAttribute('data-time-id');
      const val = (btn.getAttribute('data-time-name') || '').slice(0, 5); // HH:MM
      const [hh, mm] = val.split(':');
      document.getElementById('editHour').value = hh || '00';
      document.getElementById('editMinute').value = mm || '00';
      const editForm = document.getElementById('editForm');
      editForm.action = buildUrl(updateUrlTemplate, id);
      editForm.dataset.timeId = id;
    });
  }

  // Intercept EDIT submit
  const editForm = document.getElementById('editForm');
  if (editForm) {
    editForm.addEventListener('submit', async (e) => {
      if (editForm.dataset.confirmed === '1') return; // already confirmed
      e.preventDefault();
      const timeId = editForm.dataset.timeId;
      await showAffectedPreviewForTime(timeId, 'Editing this time will update the following courses.');
      pendingSubmitForm = editForm;
    });
  }

  // DELETE
  const deleteModal = document.getElementById('deleteModal');
  if (deleteModal) {
    deleteModal.addEventListener('show.bs.modal', function (event) {
      const btn = event.relatedTarget;
      const id = btn.getAttribute('data-time-id');
      const val = btn.getAttribute('data-time-name');
      document.getElementById('deleteName').textContent = val;
      const deleteForm = document.getElementById('deleteForm');
      deleteForm.action = buildUrl(deleteUrlTemplate, id);
      deleteForm.dataset.timeId = id;
    });
  }

  // Intercept DELETE submit
  const deleteForm = document.getElementById('deleteForm');
  if (deleteForm) {
    deleteForm.addEventListener('submit', async (e) => {
      if (deleteForm.dataset.confirmed === '1') return;
      e.preventDefault();
      const timeId = deleteForm.dataset.timeId;
      await showAffectedPreviewForTime(timeId, 'Deleting this time will detach it from the following courses.');
      pendingSubmitForm = deleteForm;
    });
  }

  function hideOpenModals() {
    document.querySelectorAll('.modal.show').forEach((el) => {
      (bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el)).hide();
    });
  }

  let pendingSubmitForm = null;

  async function showAffectedPreviewForTime(timeId, introText) {
    hideOpenModals();

    const url = buildUrl(affectedUrlTemplate, timeId);
    const res = await fetch(url, { method: 'GET', headers: { Accept: 'application/json' } });
    const data = await res.json();

    const intro = document.getElementById('affectedIntro');
    const list = document.getElementById('affectedList');
    intro.textContent = introText;
    list.innerHTML = '';

    if (!data.items || data.items.length === 0) {
      const li = document.createElement('li');
      li.className = 'text-muted';
      li.textContent = 'No courses will be affected.';
      list.appendChild(li);
    } else {
      for (const c of data.items) {
        const li = document.createElement('li');
        li.textContent = `${c.code} ${c.number} ${c.section} ${c.year} ${c.term}`.trim();
        list.appendChild(li);
      }
    }

    const previewEl = document.getElementById('affectedModal');
    const preview = bootstrap.Modal.getOrCreateInstance(previewEl);
    preview.show();

    const confirmBtn = document.getElementById('affectedConfirmBtn');
    confirmBtn.onclick = () => {
      if (pendingSubmitForm) {
        pendingSubmitForm.dataset.confirmed = '1';
        pendingSubmitForm.submit();
        pendingSubmitForm = null;
      }
      preview.hide();
    };
  }
})();
