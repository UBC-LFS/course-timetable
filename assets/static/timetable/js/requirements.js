(function () {
  const root = document.getElementById('requirements-root');
  if (!root) return;

  const levelsUrl = root.dataset.levelsUrl;
  const numbersUrl = root.dataset.numbersUrl;

  const majorSel = document.getElementById('major-select');
  const levelSel = document.getElementById('level-select');
  const clearBtn = document.getElementById('clear-filters');

  function resetLevels() {
    if (levelSel) {
      levelSel.innerHTML = '<option value="">-- Select Year Level --</option>';
    }
  }

  async function loadLevelsFor(majorName) {
    resetLevels();
    if (!levelSel) return;
    if (!majorName) {
      levelSel.disabled = true;
      return;
    }
    try {
      const resp = await fetch(`${levelsUrl}?major=${encodeURIComponent(majorName)}`);
      const data = await resp.json();
      for (const lvl of data.levels) {
        const opt = document.createElement('option');
        opt.value = opt.textContent = lvl;
        levelSel.appendChild(opt);
      }
      levelSel.disabled = data.levels.length === 0; // stays disabled if none
    } catch (e) {
      // fallback: keep it disabled on error
      levelSel.disabled = true;
    }
  }

  // On change, (re)populate year levels for the chosen major
  if (majorSel) {
    majorSel.addEventListener('change', (e) => loadLevelsFor(e.target.value));
  }

  // Clear button
  if (clearBtn && majorSel) {
    clearBtn.addEventListener('click', function () {
      majorSel.value = "";
      majorSel.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }

  // REMOVE
  document.addEventListener('DOMContentLoaded', function () {
    const modalEl = document.getElementById('confirmDetach');
    if (!modalEl || !window.bootstrap) return;

    const modal = new bootstrap.Modal(modalEl);
    const txt = document.getElementById('confirmCourseText');
    const hidCode = document.getElementById('hidCode');
    const hidNumber = document.getElementById('hidNumber');

    document.querySelectorAll('.js-open-delete').forEach((btn) => {
      btn.addEventListener('click', () => {
        const code = btn.dataset.code;
        const num = btn.dataset.number;

        if (txt) {
          txt.textContent = `${code} ${num}`;
        }
        if (hidCode) {
          hidCode.value = code;
        }
        if (hidNumber) {
          hidNumber.value = num;
        }

        modal.show();
      });
    });
  });

  // ADD
  const codeSel = document.getElementById('add-code');
  const numSel = document.getElementById('add-number');

  function resetNums() {
    if (!numSel) return;
    numSel.innerHTML = '<option value="">-- Select Number --</option>';
    numSel.disabled = true;
  }

  function resetAddForm() {
    // clear BOTH dropdowns every time the modal opens
    if (codeSel) codeSel.selectedIndex = 0; // clear Course Code
    resetNums(); // clears & disables Number
  }

  async function loadNumbersFor(codeName) {
    resetNums();
    if (!codeName || !numSel) return;
    try {
      const resp = await fetch(`${numbersUrl}?code=${encodeURIComponent(codeName)}`);
      const data = await resp.json();
      for (const n of data.numbers) {
        const opt = document.createElement('option');
        opt.value = opt.textContent = n;
        numSel.appendChild(opt);
      }
      numSel.disabled = data.numbers.length === 0;
    } catch (e) {
      numSel.disabled = true;
    }
  }

  if (codeSel) {
    codeSel.addEventListener('change', (e) => {
      loadNumbersFor(e.target.value);
    });
  }

  // In case the modal is reopened, always reset
  const addModal = document.getElementById('addCourseModal');
  if (addModal) {
    addModal.addEventListener('show.bs.modal', resetAddForm);
  }
})();
