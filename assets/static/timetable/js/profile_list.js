(function () {
  const root = document.getElementById('profiles-root');
  if (!root) return;

  const updateUrlTemplate = root.dataset.updateUrl;
  const deleteUrlTemplate = root.dataset.deleteUrl;

  function buildUrl(template, id) {
    if (!template) return '';
    return template.replace('0', id);
  }

  // EDIT
  const editModal = document.getElementById('editModal');
  if (editModal) {
    editModal.addEventListener('show.bs.modal', function (event) {
      const button = event.relatedTarget;

      const profileId = button.getAttribute('data-profile-id');
      const firstName = button.getAttribute('data-first-name');
      const lastName = button.getAttribute('data-last-name');
      const cwl = button.getAttribute('data-cwl');
      const roleId = button.getAttribute('data-role-id');

      document.getElementById('editFirstName').value = firstName;
      document.getElementById('editLastName').value = lastName;
      document.getElementById('editCwl').value = cwl;

      const roleSelect = document.getElementById('editRole');
      if (roleId) {
        roleSelect.value = roleId;
      } else {
        roleSelect.value = '';
      }

      const form = document.getElementById('editForm');
      form.action = buildUrl(updateUrlTemplate, profileId);
    });
  }

  // DELETE
  const deleteModal = document.getElementById('deleteModal');
  if (deleteModal) {
    deleteModal.addEventListener('show.bs.modal', function (event) {
      const button = event.relatedTarget;

      const profileId = button.getAttribute('data-profile-id');
      const firstName = button.getAttribute('data-first-name');
      const lastName = button.getAttribute('data-last-name');
      const cwl = button.getAttribute('data-cwl');
      const roleName = button.getAttribute('data-role-name');

      document.getElementById('deleteFirstName').textContent = firstName;
      document.getElementById('deleteLastName').textContent = lastName;
      document.getElementById('deleteCwl').textContent = cwl;
      document.getElementById('deleteRole').textContent = roleName;

      const form = document.getElementById('deleteForm');
      form.action = buildUrl(deleteUrlTemplate, profileId);
    });
  }
})();
