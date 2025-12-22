(function () {
  const root = document.getElementById('course-years-root');
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
      const btn = event.relatedTarget;
      const id = btn.getAttribute('data-year-id');
      const val = btn.getAttribute('data-year-name');
      document.getElementById('editYear').value = val;
      const editForm = document.getElementById('editForm');
      editForm.action = buildUrl(updateUrlTemplate, id);
      editForm.dataset.yearId = id;
    });
  }

  // Intercept EDIT submit
  const editForm = document.getElementById('editForm');
  if (editForm) {
    editForm.addEventListener('submit', async (e) => {
      if (editForm.dataset.confirmed === '1') return; // already confirmed
      e.preventDefault();
      const yearId = editForm.dataset.yearId;
      await showAffectedPreviewForYear(yearId, 'Editing this year will update the following courses.');
      pendingSubmitForm = editForm;
    });
  }

  // DELETE
  const deleteModal = document.getElementById('deleteModal');
  if (deleteModal) {
    deleteModal.addEventListener('show.bs.modal', function (event) {
      const btn = event.relatedTarget;
      const id = btn.getAttribute('data-year-id');
      const val = btn.getAttribute('data-year-name');
      document.getElementById('deleteName').textContent = val;
      const deleteForm = document.getElementById('deleteForm');
      deleteForm.action = buildUrl(deleteUrlTemplate, id);
      deleteForm.dataset.yearId = id;
    });
  }

  // Intercept DELETE submit
  const deleteForm = document.getElementById('deleteForm');
  if (deleteForm) {
    deleteForm.addEventListener('submit', async (e) => {
      if (deleteForm.dataset.confirmed === '1') return;
      e.preventDefault();
      const yearId = deleteForm.dataset.yearId;
      await showAffectedPreviewForYear(yearId, 'Deleting this year will detach it from the following courses.');
      pendingSubmitForm = deleteForm;
    });
  }

  function hideOpenModals() {
    document.querySelectorAll('.modal.show').forEach((el) => {
      (bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el)).hide();
    });
  }

  let pendingSubmitForm = null;

  async function showAffectedPreviewForYear(yearId, introText) {
    hideOpenModals();

    const url = buildUrl(affectedUrlTemplate, yearId);
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
