(function () {
  const root = document.getElementById('course-codes-root');
  if (!root) return;

  const updateUrlTemplate = root.dataset.updateUrl;
  const deleteUrlTemplate = root.dataset.deleteUrl;
  const affectedUrlTemplate = root.dataset.affectedUrl;

  function buildUrl(template, id) {
    if (!template) return '';
    return template.replace('0', id);
  }

  // CREATE
  const createModal = document.getElementById('createModal');
  if (createModal) {
    createModal.addEventListener('show.bs.modal', function () {
      const DEFAULT = '#A8A8A8';
      const picker = document.getElementById('createColorPicker');
      const hidden = document.getElementById('createColorHidden');

      function apply(val) {
        const norm = val.toUpperCase();
        picker.value = norm;
        hidden.value = norm;
      }

      apply(DEFAULT);
      picker.oninput = () => apply(picker.value);
    });
  }

  // EDIT
  const editModal = document.getElementById('editModal');
  if (editModal) {
    editModal.addEventListener('show.bs.modal', function (event) {
      const btn = event.relatedTarget;
      const id = btn.getAttribute('data-code-id');
      const name = btn.getAttribute('data-code-name');
      const color = btn.getAttribute('data-code-color').toUpperCase();

      document.getElementById('editName').value = name;
      const form = document.getElementById('editForm');
      form.action = buildUrl(updateUrlTemplate, id);

      form.dataset.codeId = id;

      const picker = document.getElementById('editColorPicker');
      const hidden = document.getElementById('editColorHidden');

      function apply(val) {
        const norm = val.toUpperCase();
        picker.value = norm;
        hidden.value = norm;
      }

      apply(color);
      picker.oninput = () => apply(picker.value);
    });
  }

  // Intercept EDIT submit
  const editForm = document.getElementById('editForm');
  if (editForm) {
    editForm.addEventListener('submit', async (e) => {
      if (editForm.dataset.confirmed === '1') return; // already confirmed
      e.preventDefault();
      const codeId = editForm.dataset.codeId;
      await showAffectedPreviewForCode(codeId, 'Editing this code will update the following courses.');
      pendingSubmitForm = editForm;
    });
  }

  // DELETE
  const deleteModal = document.getElementById('deleteModal');
  if (deleteModal) {
    deleteModal.addEventListener('show.bs.modal', function (event) {
      const btn = event.relatedTarget;
      const id = btn.getAttribute('data-code-id');
      const name = btn.getAttribute('data-code-name');
      document.getElementById('deleteName').textContent = name;

      const deleteForm = document.getElementById('deleteForm');
      deleteForm.action = buildUrl(deleteUrlTemplate, id);
      deleteForm.dataset.codeId = id;
    });
  }

  // Intercept DELETE submit
  const deleteForm = document.getElementById('deleteForm');
  if (deleteForm) {
    deleteForm.addEventListener('submit', async (e) => {
      if (deleteForm.dataset.confirmed === '1') return;
      e.preventDefault();
      const codeId = deleteForm.dataset.codeId;
      await showAffectedPreviewForCode(codeId, 'Deleting this code will detach it from the following courses.');
      pendingSubmitForm = deleteForm;
    });
  }

  document.querySelectorAll('.cc-swatch').forEach((el) => {
    const val = el.dataset.color.toUpperCase();
    el.style.backgroundColor = val;
  });

  function hideOpenModals() {
    document.querySelectorAll('.modal.show').forEach((el) => {
      (bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el)).hide();
    });
  }

  let pendingSubmitForm = null;

  async function showAffectedPreviewForCode(codeId, introText) {
    hideOpenModals();

    const url = buildUrl(affectedUrlTemplate, codeId);
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
