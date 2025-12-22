// Clear Button
(function () {
  const clearBtn = document.getElementById('clear-filters');
  if (!clearBtn) return;

  clearBtn.addEventListener('click', function () {
    const Sel = document.getElementById('id_name');
    if (Sel) {
      Sel.value = "";
      Sel.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
})();
