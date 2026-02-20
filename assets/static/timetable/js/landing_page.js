// setup for timetable grid outline
(function () {
  const items = document.querySelectorAll('.course-item');

  // helper: turn #RRGGBB into rgba(...) with a given alpha
  function hexToRgba(hex, a) {
    const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex || '');
    if (!m) return hex; // fallback to whatever was passed
    const r = parseInt(m[1], 16);
    const g = parseInt(m[2], 16);
    const b = parseInt(m[3], 16);
    return `rgba(${r}, ${g}, ${b}, ${a})`;
  }

  items.forEach(el => {
    const h = el.dataset.height;
    const t = el.dataset.top;
    const w = el.dataset.width;
    const bg = el.dataset.bg;
    const z = el.dataset.z;

    if (h) el.style.height = h + 'px';
    if (t) el.style.marginTop = t + 'px';
    if (w) el.style.width = w + '%';

    // TRANSPARENCY + colored stripe
    if (bg) {
      el.style.backgroundColor = hexToRgba(bg, 0.35); // translucent fill
      el.style.borderLeft = `4px solid ${bg}`; // solid accent bar
    }
    if (z) el.style.zIndex = z;
  });
})();

// Academic Year and Term filter
(function () {
  const dataHost = document.getElementById('landing-page-data');
  if (!dataHost) return;

  const termsUrl = dataHost.dataset.termsUrl;
  if (!termsUrl) return;

  const yearSel = document.getElementById('year-select');
  const termSel = document.getElementById('term-select');

  // helper: initialize Select2 on #term-select
  function initSelect2() {
    // destroy if already initialized
    if ($(termSel).hasClass('select2-hidden-accessible')) {
      $(termSel).select2('destroy');
    }
    $(termSel).select2({
      placeholder: 'Select Terms',
      width: '100%',
      allowClear: true
    });
  }

  // Initial boot (page load): if a year is preselected, init Select2 with those options
  initSelect2();

  // If the select is disabled at load, Select2 mirrors that; nothing else to do

  // When Academic Year changes: fetch terms, repopulate, enable + re-init Select2
  async function loadTermsFor(year) {
    termSel.innerHTML = '';
    termSel.disabled = true;
    if ($(termSel).hasClass('select2-hidden-accessible')) {
      $(termSel).val(null).trigger('change');
    }

    if (!year) {
      initSelect2();
      return;
    }

    try {
      const resp = await fetch(termsUrl + '?year=' + encodeURIComponent(year));
      const data = await resp.json();

      // build options
      data.terms.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t;
        opt.textContent = t;
        termSel.appendChild(opt);
      });

      // enable + re-init
      termSel.disabled = (data.terms.length === 0);
      initSelect2();

      // nothing preselected after changing year
      $(termSel).val(null).trigger('change');
    } catch (e) {
      // on error keep disabled and empty
      termSel.disabled = true;
      initSelect2();
    }
  }

  yearSel?.addEventListener('change', (e) => loadTermsFor(e.target.value));
})();

// By Course filter
(function () {
  const dataHost = document.getElementById('landing-page-data');
  if (!dataHost) return;

  const urlNums = dataHost.dataset.numbersUrl;
  if (!urlNums) return;

  let preloadMap = {};
  try {
    preloadMap = JSON.parse(dataHost.dataset.numbersByCode || '{}');
  } catch (e) {
    preloadMap = {};
  }

  const termSel = $('#term-select');
  const linesHost = document.getElementById('by-course-lines');
  const tpl = document.getElementById('by-course-template');
  const hidden = document.getElementById('courseFiltersJson');

  let nextLineId = 0;

  function hasTerms() {
    const v = termSel.val();
    return Array.isArray(v) && v.length > 0;
  }

  function initNumSelect2(selectEl) {
    const $el = $(selectEl);
    if ($el.hasClass('select2-hidden-accessible')) $el.select2('destroy');
    $el.select2({ placeholder: 'Select Numbers', width: '100%', allowClear: true });
  }

  // Populate Number select with concrete course numbers + “100 level / 200 level …”
  function fillNumberSelect(selectEl, numbers) {
    selectEl.innerHTML = '';

    const levelDigits = new Set();
    const concreteValues = [];

    // 1) Scan numbers, remember concrete values and which levels exist
    (numbers || []).forEach(n => {
      if (!n) return;
      const value = String(n).trim();
      if (!value) return;

      concreteValues.push(value);

      const m = value.match(/^(\d)/);
      if (m && m[1] !== '0') {
        levelDigits.add(m[1]);
      }
    });

    // 2) Add synthetic “X00 level” options only for levels that exist
    Array.from(levelDigits).sort().forEach(d => {
      const opt = document.createElement('option');
      opt.value = 'L' + d; // special token understood by the server
      opt.textContent = d + '00 level';
      opt.dataset.level = 'true';
      selectEl.appendChild(opt);
    });

    // 3) Then add all the concrete course numbers
    concreteValues.forEach(value => {
      const opt = document.createElement('option');
      opt.value = value;
      opt.textContent = value;
      selectEl.appendChild(opt);
    });
  }

  async function loadNumbersInto(selectEl, code) {
    selectEl.innerHTML = '';
    selectEl.disabled = true;
    initNumSelect2(selectEl);
    if (!code) return;

    try {
      const resp = await fetch(urlNums + '?code=' + encodeURIComponent(code));
      const data = await resp.json();
      fillNumberSelect(selectEl, data.numbers);
      selectEl.disabled = (data.numbers.length === 0);
      initNumSelect2(selectEl);
    } catch (e) {
      selectEl.disabled = true;
      initNumSelect2(selectEl);
    }
  }

  function setRowEnabled(row, enabled) {
    const code = row.querySelector('.js-course-code');
    const number = row.querySelector('.js-course-number');
    const addBtn = row.querySelector('.js-add-line');
    const rmBtn = row.querySelector('.js-remove-line');

    code.disabled = !enabled;
    addBtn.disabled = !enabled;

    // number depends on code; if disabling the row, also clear and disable number
    if (!enabled) {
      number.innerHTML = '';
      number.disabled = true;
      $(number).val(null).trigger('change');
      initNumSelect2(number);
    }
    if (row === linesHost.firstElementChild) {
      rmBtn.classList.add('d-none');
    } else {
      rmBtn.classList.remove('d-none');
      addBtn.classList.add('d-none');
    }
  }

  function applyTermEnablement() {
    const enabled = hasTerms();
    if (!enabled) {
      // hard reset to canonical state: one disabled row, no data
      linesHost.innerHTML = '';
      const row = makeRow(null);
      linesHost.appendChild(row);
      setRowEnabled(row, false);
      hidden.value = '';
      return;
    }
    [...linesHost.children].forEach(row => setRowEnabled(row, enabled));
  }

  function makeRow(prefill) {
    const node = tpl.content.firstElementChild.cloneNode(true);
    const lineId = nextLineId++;
    const code = node.querySelector('.js-course-code');
    const number = node.querySelector('.js-course-number');
    code.dataset.line = number.dataset.line = String(lineId);

    // prefill
    if (prefill && prefill.code) {
      code.value = prefill.code;
    }
    initNumSelect2(number);

    code.addEventListener('change', () => {
      const pre = preloadMap[code.value];
      if (pre && pre.length) {
        fillNumberSelect(number, pre);
        number.disabled = false;
        initNumSelect2(number);
      } else {
        loadNumbersInto(number, code.value);
      }
    });

    node.querySelector('.js-add-line').addEventListener('click', () => {
      linesHost.appendChild(makeRow(null));
      applyTermEnablement(); // apply enable/disable based on current terms
    });

    node.querySelector('.js-remove-line').addEventListener('click', () => {
      node.remove();
      // if no lines left, ensure at least one initial line exists
      if (!linesHost.children.length) linesHost.appendChild(makeRow(null));
      applyTermEnablement();
    });

    // if prefill includes numbers, load and select after load
    if (prefill && prefill.code) {
      const pre = preloadMap[prefill.code];
      if (pre && pre.length) {
        fillNumberSelect(number, pre);
        number.disabled = false;
        initNumSelect2(number);
        if (prefill.numbers && prefill.numbers.length) {
          $(number).val(prefill.numbers).trigger('change');
        }
      } else {
        loadNumbersInto(number, prefill.code).then(() => {
          if (prefill.numbers && prefill.numbers.length) {
            $(number).val(prefill.numbers).trigger('change');
          }
        });
      }
    }

    return node;
  }

  // Serialize lines → hidden input before submit
  function serializeLines() {
    if (!hasTerms()) {
      hidden.value = '';
      return;
    }
    const result = [];
    [...linesHost.children].forEach(row => {
      const code = row.querySelector('.js-course-code').value.trim();
      const number = row.querySelector('.js-course-number');
      const nums = $(number).val() || [];
      if (code || (nums && nums.length)) {
        result.push({ code, numbers: nums });
      }
    });
    hidden.value = JSON.stringify(result);
  }

  // 1) Build initial row
  linesHost.appendChild(makeRow(null));

  // 2) If server returned prior selections, rebuild them — but ONLY when Term has values
  try {
    const pre = hidden.value ? JSON.parse(hidden.value) : [];
    if (hasTerms() && Array.isArray(pre) && pre.length) {
      // replace the single empty row with prefilled rows
      linesHost.innerHTML = '';
      pre.forEach(item => linesHost.appendChild(makeRow({ code: item.code, numbers: item.numbers || [] })));
    }
  } catch (e) {
    // ignore
  }

  // 3) Tie enable/disable to Term changes
  termSel.on('change', applyTermEnablement);
  applyTermEnablement();

  // 4) On form submit: serialize
  const form = document.getElementById('landing-page-form');
  form?.addEventListener('submit', serializeLines);
})();

// By Major
(function () {
  const dataHost = document.getElementById('landing-page-data');
  if (!dataHost) return;

  const levelsUrl = dataHost.dataset.levelsUrl;
  if (!levelsUrl) return;

  const termSel = $('#term-select');
  const nameSel = document.getElementById('prog-name');
  const levelSel = document.getElementById('prog-level');

  function disableMajorFilters() {
    // reset name
    if (nameSel) {
      nameSel.value = '';
      nameSel.disabled = true;
    }
    // reset level
    if (levelSel) {
      levelSel.innerHTML = '<option value="">-- Select Year Level --</option>';
      levelSel.disabled = true;
    }
  }

  function enableMajorName() {
    if (nameSel) {
      nameSel.disabled = false;
    }
    // level still depends on name selection — we keep it as-is here
    if (nameSel && !nameSel.value) {
      levelSel.innerHTML = '<option value="">-- Select Year Level --</option>';
      levelSel.disabled = true;
    }
  }

  function updateFromTerms() {
    const vals = termSel.val();
    const hasTerms = Array.isArray(vals) && vals.length > 0;
    if (hasTerms) {
      enableMajorName();
    } else {
      disableMajorFilters();
    }
  }

  termSel.on('change', updateFromTerms);

  function resetLevels() {
    levelSel.innerHTML = '<option value="">-- Select Year Level --</option>';
    levelSel.disabled = true;
  }

  async function loadLevelsFor(majorName) {
    resetLevels();
    if (!majorName) return;

    try {
      const resp = await fetch(levelsUrl + '?major=' + encodeURIComponent(majorName));
      const data = await resp.json();
      data.levels.forEach(l => {
        const opt = document.createElement('option');
        opt.value = opt.textContent = l;
        levelSel.appendChild(opt);
      });
      levelSel.disabled = data.levels.length === 0;
    } catch (e) {
      resetLevels();
    }
  }

  nameSel?.addEventListener('change', e => loadLevelsFor(e.target.value));
})();

// Clear Button
(function () {
  const clearBtn = document.getElementById('clear-filters');
  if (!clearBtn) return;

  clearBtn.addEventListener('click', function () {
    // Reset Academic Year
    const yearSel = document.getElementById('year-select');
    if (yearSel) {
      yearSel.value = '';
      yearSel.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
})();

// modals
(function () {

  const editModal = document.getElementById('editModal');
  if(editModal) {
    editModal.addEventListener('show.bs.modal', function (event) {
      const courseFields = ['term', 'day', 'start_time', 'end_time', 'query'] 
      const button = event.relatedTarget;
      const course_id = button.getAttribute(`data-course-id`); 

      // TODO: If anyone figures out a way to not hardcode this link, then you should probably implement it 
      const link = `update_modal/${course_id}/`;
      document.getElementById('editForm').action = link;

      // prefill form fields
      for(const field of courseFields) {
        const attr = `data-course-${field}`;
        if (field == 'day') {

          const attrValues = new Set(button.getAttribute(attr).split(',').map(s => s.trim()).map(Number).map(x => x-1));
          console.log(attrValues);

          for(const day of [0,1,2,3,4]) {
            const id = `id_day_${day}`;
            if(attrValues.has(day)){
              document.getElementById(id).checked = true;
            } else {
              document.getElementById(id).checked = false;
            }
          }

        } else if (field == 'query') {
          const id = "id_query";
          const query = window.location.search;
          document.getElementById(id).value = query;
        } else {
          const id = `id_${field}`;
          const attrValue = button.getAttribute(attr);
          document.getElementById(id).value = attrValue;
        }
      }

      // Update title of course we are editing
      // document.getElementById('editForm').querySelector('h5').content += `${editModal.dataset.courseCodeName} ${editModal.dataset.courseNumberName} ${editModal.dataset.courseSectionName}`
    });
  }
})();

