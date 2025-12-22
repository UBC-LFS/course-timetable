(function () {
  const root = document.getElementById('course-terms-root');
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
      const termId = button.getAttribute('data-term-id');
      const termName = button.getAttribute('data-term-name');
      document.getElementById('editName').value = termName;
      const editForm = document.getElementById('editForm');
      editForm.action = buildUrl(updateUrlTemplate, termId);
      // stash the term id for preview use
      editForm.dataset.termId = termId;
    });
  }

  // Intercept Edit submit
  const editForm = document.getElementById('editForm');
  if (editForm) {
    editForm.addEventListener('submit', async function (e) {
      if (editForm.dataset.confirmed === '1') return; // already confirmed
      e.preventDefault();

      const termId = editForm.dataset.termId;
      await showAffectedPreview(termId, 'Editing this term will update the following courses.');
      // When user clicks Confirm in the preview, we'll submit for real.
      pendingSubmitForm = editForm;
    });
  }

  // DELETE
  const deleteModal = document.getElementById('deleteModal');
  if (deleteModal) {
    deleteModal.addEventListener('show.bs.modal', function (event) {
      const button = event.relatedTarget;
      const termId = button.getAttribute('data-term-id');
      const termName = button.getAttribute('data-term-name');
      document.getElementById('deleteName').textContent = termName;
      const form = document.getElementById('deleteForm');
      form.action = buildUrl(deleteUrlTemplate, termId);
      form.dataset.termId = termId;
    });
  }

  const deleteForm = document.getElementById('deleteForm');
  if (deleteForm) {
    deleteForm.addEventListener('submit', async function (e) {
      if (deleteForm.dataset.confirmed === '1') return;
      e.preventDefault();

      const termId = deleteForm.dataset.termId;
      await showAffectedPreview(termId, 'Deleting this term will detach it from the following courses.');
      pendingSubmitForm = deleteForm;
    });
  }

  function hideOpenModals() {
    document.querySelectorAll('.modal.show').forEach((el) => {
      (bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el)).hide();
    });
  }

  let pendingSubmitForm = null;

  async function showAffectedPreview(termId, introText) {
    hideOpenModals(); // ensure edit/delete is fully closed

    // fetch affected courses
    const url = buildUrl(affectedUrlTemplate, termId);
    const res = await fetch(url, { method: 'GET', headers: { Accept: 'application/json' } });
    const data = await res.json();

    // fill modal
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
        // e.g., "LFS_V 100 001 2025 T1"
        li.textContent = `${c.code} ${c.number} ${c.section} ${c.year} ${c.term}`.trim();
        list.appendChild(li);
      }
    }

    const previewEl = document.getElementById('affectedModal');
    const preview = bootstrap.Modal.getOrCreateInstance(previewEl);
    preview.show();

    // Confirm button submits whatever form triggered the preview
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
