(function () {
  const root = document.getElementById('major-names-root');
  if (!root) return;

  const updateUrlTemplate = root.dataset.updateUrl;
  const deleteUrlTemplate = root.dataset.deleteUrl;
  const affectedUrlTemplate = root.dataset.affectedUrl;

  function buildUrl(template, id) {
    if (!template) return '';
    return template.replace('0', id);
  }

  // EDIT
  const editModal = document.getElementById('editModal');
  if (editModal) {
    editModal.addEventListener('show.bs.modal', function (event) {
      const button = event.relatedTarget;
      const majorNameId = button.getAttribute('data-major-name-id');
      const majorNameName = button.getAttribute('data-major-name-name');
      document.getElementById('editName').value = majorNameName;
      const editForm = document.getElementById('editForm');
      editForm.action = buildUrl(updateUrlTemplate, majorNameId);
      editForm.dataset.majorNameId = majorNameId;
    });
  }

  // Intercept EDIT submit
  const editForm = document.getElementById('editForm');
  if (editForm) {
    editForm.addEventListener('submit', async (e) => {
      if (editForm.dataset.confirmed === '1') return; // already confirmed
      e.preventDefault();
      const majorNameId = editForm.dataset.majorNameId;
      await showAffectedPreviewForMajorName(majorNameId, 'Editing this name will update the following majors.');
      pendingSubmitForm = editForm;
    });
  }

  // DELETE
  const deleteModal = document.getElementById('deleteModal');
  if (deleteModal) {
    deleteModal.addEventListener('show.bs.modal', function (event) {
      const button = event.relatedTarget;
      const majorNameId = button.getAttribute('data-major-name-id');
      const majorNameName = button.getAttribute('data-major-name-name');
      document.getElementById('deleteName').textContent = majorNameName;
      const deleteForm = document.getElementById('deleteForm');
      deleteForm.action = buildUrl(deleteUrlTemplate, majorNameId);
      deleteForm.dataset.majorNameId = majorNameId;
    });
  }

  // Intercept DELETE submit
  const deleteForm = document.getElementById('deleteForm');
  if (deleteForm) {
    deleteForm.addEventListener('submit', async (e) => {
      if (deleteForm.dataset.confirmed === '1') return;
      e.preventDefault();
      const majorNameId = deleteForm.dataset.majorNameId;
      await showAffectedPreviewForMajorName(majorNameId, 'Deleting this name will detach it from the following majors.');
      pendingSubmitForm = deleteForm;
    });
  }

  function hideOpenModals() {
    document.querySelectorAll('.modal.show').forEach((el) => {
      (bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el)).hide();
    });
  }

  let pendingSubmitForm = null;

  async function showAffectedPreviewForMajorName(majorNameId, introText) {
    hideOpenModals();

    const url = buildUrl(affectedUrlTemplate, majorNameId);
    const res = await fetch(url, { method: 'GET', headers: { Accept: 'application/json' } });
    const data = await res.json();

    const intro = document.getElementById('affectedIntro');
    const list = document.getElementById('affectedList');
    intro.textContent = introText;
    list.innerHTML = '';

    if (!data.items || data.items.length === 0) {
      const li = document.createElement('li');
      li.className = 'text-muted';
      li.textContent = 'No majors will be affected.';
      list.appendChild(li);
    } else {
      for (const m of data.items) {
        const li = document.createElement('li');
        li.textContent = `${m.major_name} ${m.year_level}`.trim();
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
