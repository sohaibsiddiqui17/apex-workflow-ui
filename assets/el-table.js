/* ---------------------------------------------------------------------------
   el-table.js
   Renders the exact DOM shape Element UI 2.x produces for <el-table>, so that
   selectors written against this mock also work against the production
   X-Control grid.

   Reproduced faithfully (verified against the production capture in
   New DOM Structure/Import_Confirm_files/importConfirm.html):

     - split .el-table__header-wrapper / .el-table__body-wrapper tables
     - a SECOND complete copy of the table inside .el-table__fixed
     - .el-table_<index>_column_<n> positional classes on every th and td
     - td.el-table__cell > div.cell wrappers
     - the is-hidden inversion:
           main table  -> selection column is-hidden, data columns visible
           fixed clone -> selection column visible, data columns is-hidden
       This means a scraper reads DATA from .el-table__body-wrapper but must
       click row CHECKBOXES inside .el-table__fixed.
     - a trailing th.gutter in the main header only
     - full .el-select-dropdown option lists inside filterable headers, in both
       the main header and the fixed clone, exactly as the real page emits them
   --------------------------------------------------------------------------- */

(function (root) {
  'use strict';

  function esc(v) {
    if (v === null || v === undefined) return '';
    return String(v)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ---------------------------------------------------------------- filters */

  function filterWidget(col, scope, cur) {
    var dv = scope ? ' ' + scope + '=""' : '';
    // `cur` re-seeds the widget after a re-render. render() rebuilds innerHTML
    // wholesale, so without this every keystroke in a filter box would clear it.
    var curText = (cur === null || cur === undefined || typeof cur === 'object') ? '' : String(cur);

    if (col.filter === 'select') {
      var items = (col.options || []).map(function (o) {
        return '<li' + dv + ' class="el-select-dropdown__item"><span>' + esc(o) + '</span></li>';
      }).join('');
      return '' +
        '<div' + dv + ' class="el-select el-select--mini">' +
          '<div class="el-input el-input--mini el-input--suffix">' +
            '<input type="text" readonly="readonly" autocomplete="off" placeholder="Please select" class="el-input__inner" value="' + esc(curText) + '">' +
            '<span class="el-input__suffix"><span class="el-input__suffix-inner">' +
              '<i class="el-select__caret el-input__icon el-icon-arrow-up"></i>' +
            '</span></span>' +
          '</div>' +
          '<div class="el-select-dropdown el-popper" style="display: none;">' +
            '<div class="el-scrollbar"><div class="el-scrollbar__wrap">' +
              '<ul class="el-scrollbar__view el-select-dropdown__list">' + items + '</ul>' +
            '</div></div>' +
          '</div>' +
        '</div>';
    }

    if (col.filter === 'daterange') {
      var range = (cur && typeof cur === 'object') ? cur : {};
      return '' +
        '<div' + dv + ' class="hdr-range">' +
          '<div class="el-input el-input--mini">' +
            '<input type="text" autocomplete="off" placeholder="Start date" class="el-input__inner" value="' + esc(range.start || '') + '">' +
          '</div>' +
          '<div class="el-input el-input--mini">' +
            '<input type="text" autocomplete="off" placeholder="End date" class="el-input__inner" value="' + esc(range.end || '') + '">' +
          '</div>' +
        '</div>';
    }

    if (col.filter === 'text') {
      return '' +
        '<div' + dv + ' class="el-input el-input--mini el-input--suffix">' +
          '<input type="text" autocomplete="off" placeholder="filter column" class="el-input__inner" value="' + esc(curText) + '">' +
          '<span class="el-input__suffix"><span class="el-input__suffix-inner">' +
            '<i class="el-input__icon el-icon-search"></i>' +
          '</span></span>' +
        '</div>';
    }

    return '';
  }

  /* ---------------------------------------------------------------- header */

  function headerCell(col, n, idx, scope, hidden, cur) {
    var dv = scope ? ' ' + scope + '=""' : '';
    var cls = ['el-table_' + idx + '_column_' + n, 'is-center'];
    if (col.type === 'selection') cls.push('el-table-column--selection');
    if (hidden) cls.push('is-hidden');
    cls.push('is-leaf', 'el-table__cell');

    var inner;
    if (col.type === 'selection') {
      inner = '<label class="el-checkbox">' +
                '<span class="el-checkbox__input">' +
                  '<span class="el-checkbox__inner"></span>' +
                  '<input type="checkbox" aria-hidden="false" class="el-checkbox__original" value="">' +
                '</span>' +
              '</label>';
    } else {
      inner = '<span' + dv + '>' + esc(col.label) + '</span>';
      if (col.filter === 'daterange') inner += '<span' + dv + '>-</span>';
      inner += filterWidget(col, scope, cur);
    }

    return '<th colspan="1" rowspan="1" class="' + cls.join(' ') + '">' +
             '<div class="cell">' + inner + '</div>' +
           '</th>';
  }

  /* ------------------------------------------------------------------ body */

  function bodyCell(col, n, idx, row, rowIndex, scope, hidden) {
    var dv = scope ? ' ' + scope + '=""' : '';
    var cls = ['el-table_' + idx + '_column_' + n, 'is-center'];
    if (col.type === 'selection') cls.push('el-table-column--selection');
    if (hidden) cls.push('is-hidden');
    cls.push('el-table__cell');

    var inner;
    if (col.type === 'selection') {
      inner = '<label class="el-checkbox">' +
                '<span class="el-checkbox__input">' +
                  '<span class="el-checkbox__inner"></span>' +
                  '<input type="checkbox" aria-hidden="false" class="el-checkbox__original" value="" ' +
                    'data-row-index="' + rowIndex + '">' +
                '</span>' +
              '</label>';
    } else if (col.type === 'link') {
      inner = '<a' + dv + ' to="" params="()=&gt;{}" class="el-link el-link--primary is-underline apex_link_mini">' +
                '<!---->' +
                '<span class="el-link--inner"><span' + dv + '>' + esc(row[col.key]) + '</span></span>' +
                '<!---->' +
              '</a>';
    } else if (col.type === 'tags') {
      var raw = row[col.key];
      var list = raw ? String(raw).split(',') : [];
      // Separated by a comma text node, not just adjacent spans: innerText
      // concatenates adjacent inline elements, which would turn
      // "1F SENT" + "ISC SS" into "1F SENTISC SS" for anything scraping the cell.
      inner = list.map(function (t) {
        return '<span class="el-tag el-tag--info">' + esc(t.trim()) + '</span>';
      }).join(', ');
    } else {
      inner = esc(row[col.key]);
    }

    return '<td rowspan="1" colspan="1" class="' + cls.join(' ') + '">' +
             '<div class="cell">' + inner + '</div>' +
           '</td>';
  }

  function colgroup(columns, idx) {
    return '<colgroup>' + columns.map(function (c, i) {
      return '<col name="el-table_' + idx + '_column_' + (i + 1) + '" width="' + (c.width || 100) + '">';
    }).join('') + '</colgroup>';
  }

  /* ---------------------------------------------------------------- render */

  function render(cfg) {
    var mount   = cfg.mount;
    var columns = cfg.columns;
    var rows    = cfg.rows || [];
    var idx     = cfg.tableIndex || 1;
    var scope   = cfg.scope || '';
    var fixedN  = cfg.fixedCount === undefined ? 1 : cfg.fixedCount;
    var dv      = scope ? ' ' + scope + '=""' : '';

    var totalW = columns.reduce(function (a, c) { return a + (c.width || 100); }, 0);
    var fixedW = columns.slice(0, fixedN).reduce(function (a, c) { return a + (c.width || 100); }, 0);
    var bodyH  = cfg.bodyHeight || 424;
    var cg     = colgroup(columns, idx);

    /* --- main header: selection column hidden, data columns visible ------- */
    var filters = cfg.filters || {};
    var mainHead = columns.map(function (c, i) {
      return headerCell(c, i + 1, idx, scope, i < fixedN, c.key ? filters[c.key] : null);
    }).join('') + '<th class="el-table__cell gutter" style="width: 0px; display: none;"></th>';

    /* --- main body: same inversion ---------------------------------------- */
    var mainBody = rows.map(function (r, ri) {
      return '<tr class="el-table__row">' + columns.map(function (c, i) {
        return bodyCell(c, i + 1, idx, r, ri, scope, i < fixedN);
      }).join('') + '</tr>';
    }).join('');

    /* --- fixed clone: selection column visible, data columns hidden ------- */
    var fixHead = columns.map(function (c, i) {
      return headerCell(c, i + 1, idx, scope, i >= fixedN, c.key ? filters[c.key] : null);
    }).join('');

    var fixBody = rows.map(function (r, ri) {
      return '<tr class="el-table__row">' + columns.map(function (c, i) {
        return bodyCell(c, i + 1, idx, r, ri, scope, i >= fixedN);
      }).join('') + '</tr>';
    }).join('');

    var empty = rows.length ? '' :
      '<div class="el-table__empty-block" style="width: 100%;">' +
        '<span class="el-table__empty-text">No Data</span>' +
      '</div>';

    mount.className = 'el-table el-table--fit el-table--scrollable-x el-table--enable-row-hover el-table--border';
    if (scope) mount.setAttribute(scope, '');

    mount.innerHTML = '' +
      '<div class="hidden-columns"><!----></div>' +

      '<div class="el-table__header-wrapper">' +
        '<table cellspacing="0" cellpadding="0" border="0" class="el-table__header" style="width: ' + totalW + 'px;">' +
          cg +
          '<thead class="has-gutter"><tr>' + mainHead + '</tr></thead>' +
        '</table>' +
      '</div>' +

      '<div class="el-table__body-wrapper is-scrolling-left" style="height: ' + bodyH + 'px;">' +
        '<table cellspacing="0" cellpadding="0" border="0" class="el-table__body" style="width: ' + totalW + 'px;">' +
          cg +
          '<tbody>' + mainBody + '</tbody>' +
        '</table>' +
        empty +
        '<div class="el-table__append-wrapper"><div' + dv + '></div></div>' +
      '</div>' +

      '<div class="el-table__fixed" style="width: ' + fixedW + 'px; height: ' + (bodyH + 64) + 'px;">' +
        '<div class="el-table__fixed-header-wrapper">' +
          '<table cellspacing="0" cellpadding="0" border="0" class="el-table__header" style="width: ' + totalW + 'px;">' +
            cg +
            '<thead class="has-gutter"><tr>' + fixHead + '</tr></thead>' +
          '</table>' +
        '</div>' +
        '<div class="el-table__fixed-body-wrapper" style="top: 64px; height: ' + bodyH + 'px;">' +
          '<table cellspacing="0" cellpadding="0" border="0" class="el-table__body" style="width: ' + totalW + 'px;">' +
            cg +
            '<tbody>' + fixBody + '</tbody>' +
          '</table>' +
        '</div>' +
      '</div>';

    wireSelection(mount, cfg);
    wireDropdowns(mount);
    wireScrollSync(mount);
    // Re-baseline the change guard on every render. Without this, clearing a
    // filter and then retyping the same value would be treated as "no change".
    mount.__elFilterKey = filterKey(filters);
    wireFilters(mount, cfg);
    return mount;
  }

  /* ------------------------------------------------------- interactivity */

  /* The table is three independently overflowing boxes: the header wrapper
     (overflow:hidden), the body wrapper (overflow:auto — the only scrollbar the
     user ever touches) and the frozen-column clone (overflow:hidden). Element UI
     drives the other two off the body wrapper's scroll event; nothing here did,
     so the ~4350px of header scrolled past the viewport could never be reached
     and the frozen checkboxes stopped lining up with the rows beside them.

     Both wrappers keep overflow:hidden — production relies on that clipping, and
     the row-clone trick depends on the clone staying unscrollable — so the
     header is moved with scrollLeft (settable even on overflow:hidden) and the
     clone by transforming the table inside it rather than by giving either one a
     scrollbar of its own. */
  function wireScrollSync(mount) {
    var body = mount.querySelector('.el-table__body-wrapper');
    if (!body) return;

    var header     = mount.querySelector('.el-table__header-wrapper');
    var fixed      = mount.querySelector('.el-table__fixed');
    var fixedHead  = mount.querySelector('.el-table__fixed-header-wrapper');
    var fixedBody  = mount.querySelector('.el-table__fixed-body-wrapper');
    var fixedTable = fixedBody ? fixedBody.querySelector('table.el-table__body') : null;

    /* The clone's body sits absolutely below its own header copy. How tall that
       header is depends on the filter widgets inside it — 114px on Import
       Confirm, 99px on Update ATD&ATA, never the 64px the markup assumes — so
       measure it instead of guessing, or row 1 of the checkbox column starts
       50px above row 1 of the data. Height comes from clientHeight, which
       excludes the horizontal scrollbar the body wrapper carries and the clone
       does not, so both clip after the same row. */
    function place() {
      if (!fixed || !fixedBody) return;
      var headH = (fixedHead || header) ? (fixedHead || header).offsetHeight : 0;
      if (!headH) return;   // inside a hidden tab pane; the observer retries
      var top  = headH + 'px';
      var inner = body.clientHeight + 'px';
      var outer = (headH + body.offsetHeight) + 'px';
      if (fixedBody.style.top    !== top)   fixedBody.style.top    = top;
      if (fixedBody.style.height !== inner) fixedBody.style.height = inner;
      if (fixed.style.height     !== outer) fixed.style.height     = outer;
    }

    function sync() {
      if (header) header.scrollLeft = body.scrollLeft;
      if (fixedTable) {
        fixedTable.style.transform = body.scrollTop
          ? 'translateY(' + (-body.scrollTop) + 'px)'
          : '';
      }
      // Element UI's own shadow/edge state, kept honest rather than hardcoded.
      var max = body.scrollWidth - body.clientWidth;
      var cl  = body.classList;
      cl.toggle('is-scrolling-none',   max <= 0);
      cl.toggle('is-scrolling-left',   max > 0 && body.scrollLeft <= 0);
      cl.toggle('is-scrolling-right',  max > 0 && body.scrollLeft >= max);
      cl.toggle('is-scrolling-middle', max > 0 && body.scrollLeft > 0 && body.scrollLeft < max);
    }

    body.addEventListener('scroll', sync);

    /* Panes 2 and 3 render while their tab is hidden, so the header measures 0
       there. Re-place when the mount gains a size — which is also what a window
       resize or a re-wrapping header cell needs. */
    if (mount.__elResizeObs) mount.__elResizeObs.disconnect();
    if (typeof ResizeObserver === 'function') {
      mount.__elResizeObs = new ResizeObserver(place);
      mount.__elResizeObs.observe(mount);
    }

    place();
    sync();
  }

  /* Row checkboxes exist in both copies. Clicking either must keep the two in
     sync, exactly as Element UI does, so a bot clicking the visible one in the
     fixed clone produces the same state a human would. */
  function wireSelection(mount, cfg) {
    function setChecked(input, on) {
      input.checked = on;
      var wrap = input.closest('.el-checkbox__input');
      if (wrap) wrap.classList.toggle('is-checked', on);
    }

    function syncRow(rowIndex, on) {
      mount.querySelectorAll('.el-checkbox__original[data-row-index="' + rowIndex + '"]')
        .forEach(function (cb) { setChecked(cb, on); });
      if (typeof cfg.onSelect === 'function') cfg.onSelect(selectedIndexes(mount));
    }

    mount.querySelectorAll('.el-checkbox__original[data-row-index]').forEach(function (cb) {
      cb.addEventListener('change', function () {
        syncRow(cb.getAttribute('data-row-index'), cb.checked);
      });
    });

    // Header "select all" — present in both header copies.
    mount.querySelectorAll('thead .el-checkbox__original').forEach(function (all) {
      all.addEventListener('change', function () {
        var on = all.checked;
        mount.querySelectorAll('thead .el-checkbox__original').forEach(function (h) { setChecked(h, on); });
        mount.querySelectorAll('.el-checkbox__original[data-row-index]').forEach(function (cb) {
          setChecked(cb, on);
        });
        if (typeof cfg.onSelect === 'function') cfg.onSelect(selectedIndexes(mount));
      });
    });
  }

  function selectedIndexes(mount) {
    var seen = {};
    mount.querySelectorAll('.el-table__body-wrapper .el-checkbox__original[data-row-index]')
      .forEach(function (cb) { if (cb.checked) seen[cb.getAttribute('data-row-index')] = true; });
    // the fixed clone holds the visible checkboxes, so read those too
    mount.querySelectorAll('.el-table__fixed .el-checkbox__original[data-row-index]')
      .forEach(function (cb) { if (cb.checked) seen[cb.getAttribute('data-row-index')] = true; });
    return Object.keys(seen).map(Number).sort(function (a, b) { return a - b; });
  }

  /* Open/close behaviour for any .el-select under `scopeEl`. Works for the
     in-header column filters and equally for the pagination size picker, which
     sits outside the table. Safe to call repeatedly — already-bound selects are
     skipped. `onPick(value, selectEl)` fires when an option is chosen. */
  function bindSelects(scopeEl, onPick) {
    scopeEl.querySelectorAll('.el-select').forEach(function (sel) {
      if (sel.dataset.selectBound === '1') return;
      var input = sel.querySelector('.el-input__inner');
      var drop  = sel.querySelector('.el-select-dropdown');
      if (!input || !drop) return;
      sel.dataset.selectBound = '1';

      input.addEventListener('click', function (e) {
        e.stopPropagation();
        var isOpen = drop.style.display !== 'none';
        document.querySelectorAll('.el-select-dropdown').forEach(function (d) {
          d.style.display = 'none';
        });
        drop.style.display = isOpen ? 'none' : '';
      });

      drop.addEventListener('click', function (e) {
        var li = e.target.closest('.el-select-dropdown__item');
        if (!li) return;
        e.stopPropagation();
        var value = li.textContent.trim();
        input.value = value;
        drop.querySelectorAll('.el-select-dropdown__item').forEach(function (o) {
          o.classList.remove('selected');
        });
        li.classList.add('selected');
        drop.style.display = 'none';
        input.dispatchEvent(new Event('change', { bubbles: true }));
        if (typeof onPick === 'function') onPick(value, sel);
      });
    });
  }

  // One global outside-click handler closes every open dropdown.
  if (typeof document !== 'undefined' && !root.__elSelectOutsideBound) {
    root.__elSelectOutsideBound = true;
    document.addEventListener('click', function () {
      document.querySelectorAll('.el-select-dropdown').forEach(function (d) {
        d.style.display = 'none';
      });
    });
  }

  /* The column header filters used to be decorative — rendered, openable, and
     wired to nothing. They filter for real now.

     Column identity is derived POSITIONALLY against cfg.columns, matching the
     order the header was generated in, rather than by stamping a data-* key
     onto the markup. Production emits no such attribute, and the whole point of
     this mock is that a selector proven here also works there. */
  /* Key-order-independent identity for a filter set, so the "did anything
     change?" guard cannot be fooled by two equal sets built in a different
     order. */
  function filterKey(filters) {
    var keys = Object.keys(filters || {}).sort();
    return JSON.stringify(keys.map(function (k) { return [k, filters[k]]; }));
  }

  function wireFilters(mount, cfg) {
    if (typeof cfg.onFilter !== 'function') return;
    var columns = cfg.columns || [];

    function collect() {
      var out = {};
      var ths = mount.querySelectorAll('.el-table__header-wrapper thead tr th');
      columns.forEach(function (col, i) {
        var th = ths[i];
        if (!th || !col.key || !col.filter) return;

        if (col.filter === 'daterange') {
          var ins = th.querySelectorAll('.hdr-range .el-input__inner');
          var start = ins[0] ? ins[0].value.trim() : '';
          var end   = ins[1] ? ins[1].value.trim() : '';
          if (start || end) out[col.key] = { start: start, end: end };
          return;
        }

        var input = th.querySelector('.el-input__inner');
        var value = input ? input.value.trim() : '';
        if (value && value !== 'All') out[col.key] = value;
      });
      return out;
    }

    /* Applying a filter re-renders the table, which destroys the very input
       being typed into. Two things keep that from being felt:

         - re-render only when the filter set actually changed, so the blur
           that follows a fill() does not fire a second, pointless render that
           would swallow whatever the user clicked next;
         - put focus and caret back afterwards, addressing the input by its
           column position since the old node is gone. */
    function apply(thIndex, inputIndex, caret) {
      var next = collect();
      var key = filterKey(next);
      if (key === mount.__elFilterKey) return;
      mount.__elFilterKey = key;

      cfg.onFilter(next);

      if (thIndex === null || thIndex === undefined) return;
      var th = mount.querySelectorAll('.el-table__header-wrapper thead tr th')[thIndex];
      if (!th) return;
      var input = th.querySelectorAll('.el-input__inner')[inputIndex || 0];
      if (!input || input.readOnly) return;
      input.focus();
      try { input.setSelectionRange(caret, caret); } catch (err) { /* not a text input */ }
    }

    mount.querySelectorAll('.el-table__header-wrapper thead tr th').forEach(function (th, thIndex) {
      th.querySelectorAll('.el-input__inner').forEach(function (input, inputIndex) {
        function fire() { apply(thIndex, inputIndex, input.selectionStart); }

        if (input.readOnly) {
          // A select. bindSelects dispatches 'change' when an option is picked.
          input.addEventListener('change', fire);
          return;
        }

        /* Debounced, because Playwright's fill() and a human's keystrokes both
           arrive as 'input' — 'change' alone would never fire for fill(), which
           does not blur. */
        var timer = null;
        input.addEventListener('input', function () {
          clearTimeout(timer);
          timer = setTimeout(fire, 200);
        });
        input.addEventListener('change', function () { clearTimeout(timer); fire(); });
        input.addEventListener('keydown', function (e) {
          if (e.key === 'Enter') { clearTimeout(timer); fire(); }
        });
      });
    });
  }

  function wireDropdowns(mount) { bindSelects(mount); }

  /* Shared predicate so importConfirm and updateAtdAta agree on what a header
     filter means: substring & case-insensitive for text, exact for selects,
     lexical bounds for date ranges (the timestamps are zero-padded ISO-ish
     strings, so string comparison is date comparison). */
  function matchesFilters(row, filters) {
    return Object.keys(filters || {}).every(function (key) {
      var want = filters[key];
      var have = row[key] === null || row[key] === undefined ? '' : String(row[key]);

      if (want && typeof want === 'object') {
        if (want.start && have < want.start) return false;
        if (want.end && have > want.end + '￿') return false;
        return true;
      }
      return have.toLowerCase().indexOf(String(want).toLowerCase()) !== -1;
    });
  }

  root.ElTableMock = {
    render: render,
    selectedIndexes: selectedIndexes,
    bindSelects: bindSelects,
    matchesFilters: matchesFilters,
    esc: esc
  };
})(typeof window !== 'undefined' ? window : this);
