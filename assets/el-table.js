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

  function filterWidget(col, scope) {
    var dv = scope ? ' ' + scope + '=""' : '';

    if (col.filter === 'select') {
      var items = (col.options || []).map(function (o) {
        return '<li' + dv + ' class="el-select-dropdown__item"><span>' + esc(o) + '</span></li>';
      }).join('');
      return '' +
        '<div' + dv + ' class="el-select el-select--mini">' +
          '<div class="el-input el-input--mini el-input--suffix">' +
            '<input type="text" readonly="readonly" autocomplete="off" placeholder="Please select" class="el-input__inner">' +
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
      return '' +
        '<div' + dv + ' class="hdr-range">' +
          '<div class="el-input el-input--mini">' +
            '<input type="text" autocomplete="off" placeholder="Start date" class="el-input__inner">' +
          '</div>' +
          '<div class="el-input el-input--mini">' +
            '<input type="text" autocomplete="off" placeholder="End date" class="el-input__inner">' +
          '</div>' +
        '</div>';
    }

    if (col.filter === 'text') {
      return '' +
        '<div' + dv + ' class="el-input el-input--mini el-input--suffix">' +
          '<input type="text" autocomplete="off" placeholder="filter column" class="el-input__inner">' +
          '<span class="el-input__suffix"><span class="el-input__suffix-inner">' +
            '<i class="el-input__icon el-icon-search"></i>' +
          '</span></span>' +
        '</div>';
    }

    return '';
  }

  /* ---------------------------------------------------------------- header */

  function headerCell(col, n, idx, scope, hidden) {
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
      inner += filterWidget(col, scope);
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
    var mainHead = columns.map(function (c, i) {
      return headerCell(c, i + 1, idx, scope, i < fixedN);
    }).join('') + '<th class="el-table__cell gutter" style="width: 0px; display: none;"></th>';

    /* --- main body: same inversion ---------------------------------------- */
    var mainBody = rows.map(function (r, ri) {
      return '<tr class="el-table__row">' + columns.map(function (c, i) {
        return bodyCell(c, i + 1, idx, r, ri, scope, i < fixedN);
      }).join('') + '</tr>';
    }).join('');

    /* --- fixed clone: selection column visible, data columns hidden ------- */
    var fixHead = columns.map(function (c, i) {
      return headerCell(c, i + 1, idx, scope, i >= fixedN);
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
    return mount;
  }

  /* ------------------------------------------------------- interactivity */

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

  function wireDropdowns(mount) { bindSelects(mount); }

  root.ElTableMock = {
    render: render,
    selectedIndexes: selectedIndexes,
    bindSelects: bindSelects,
    esc: esc
  };
})(typeof window !== 'undefined' ? window : this);
