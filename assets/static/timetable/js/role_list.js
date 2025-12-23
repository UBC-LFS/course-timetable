(function () {
  const root = document.getElementById('roles-root');
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
      const roleId = button.getAttribute('data-role-id');
      const roleName = button.getAttribute('data-role-name');
      document.getElementById('editName').value = roleName;
      const editForm = document.getElementById('editForm');
      editForm.action = buildUrl(updateUrlTemplate, roleId);
      // stash the role id for preview use
      editForm.dataset.roleId = roleId;
    });
  }

  // Intercept Edit submit
  const editForm = document.getElementById('editForm');
  if (editForm) {
    editForm.addEventListener('submit', async function (e) {
      if (editForm.dataset.confirmed === '1') return; // already confirmed
      e.preventDefault();

      const roleId = editForm.dataset.roleId;
      await showAffectedPreview(roleId, 'Editing this role will update the following users.');
      // When user clicks Confirm in the preview, we'll submit for real.
      pendingSubmitForm = editForm;
    });
  }

  // DELETE
  const deleteModal = document.getElementById('deleteModal');
  if (deleteModal) {
    deleteModal.addEventListener('show.bs.modal', function (event) {
      const button = event.relatedTarget;
      const roleId = button.getAttribute('data-role-id');
      const roleName = button.getAttribute('data-role-name');
      document.getElementById('deleteName').textContent = roleName;
      const form = document.getElementById('deleteForm');
      form.action = buildUrl(deleteUrlTemplate, roleId);
      form.dataset.roleId = roleId;
    });
  }

  const deleteForm = document.getElementById('deleteForm');
  if (deleteForm) {
    deleteForm.addEventListener('submit', async function (e) {
      if (deleteForm.dataset.confirmed === '1') return;
      e.preventDefault();

      const roleId = deleteForm.dataset.roleId;
      await showAffectedPreview(roleId, 'Deleting this role will detach it from the following users.');
      pendingSubmitForm = deleteForm;
    });
  }

  function hideOpenModals() {
    document.querySelectorAll('.modal.show').forEach((el) => {
      (bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el)).hide();
    });
  }

  let pendingSubmitForm = null;

  async function showAffectedPreview(roleId, introText) {
    hideOpenModals(); // ensure edit/delete is fully closed

    // fetch affected profiles
    const url = buildUrl(affectedUrlTemplate, roleId);
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
      li.textContent = 'No users will be affected.';
      list.appendChild(li);
    } else {
      for (const p of data.items) {
        const li = document.createElement('li');
        li.textContent = `${p.first_name} ${p.last_name} ${p.username} ${p.role}`.trim();
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
