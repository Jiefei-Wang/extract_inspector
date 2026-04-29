INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Extraction Inspector</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f5f7;
      --panel: #ffffff;
      --panel-border: #d7dce3;
      --muted: #6b7280;
      --text: #1f2937;
      --accent: #0f766e;
      --accent-soft: #d1fae5;
      --active: #f59e0b;
      --shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: Inter, Arial, sans-serif;
      color: var(--text);
      background: var(--bg);
      height: 100vh;
      overflow: hidden;
    }

    .app-shell {
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr) 360px;
      gap: 12px;
      height: 100vh;
      padding: 12px;
    }

    .panel {
      min-height: 0;
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      box-shadow: var(--shadow);
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .panel-header {
      padding: 12px 14px;
      border-bottom: 1px solid var(--panel-border);
      font-size: 14px;
      font-weight: 600;
    }

    .group-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
      gap: 8px;
      padding: 12px;
      border-bottom: 1px solid var(--panel-border);
    }

    .group-button,
    .text-button {
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      background: #fff;
      color: var(--text);
      cursor: pointer;
      transition: background-color 140ms ease, border-color 140ms ease, color 140ms ease;
    }

    .group-button {
      min-height: 40px;
      font-size: 13px;
      font-weight: 600;
    }

    .group-button.active,
    .text-button.active {
      background: var(--accent-soft);
      border-color: var(--accent);
      color: #115e59;
    }

    .filter-bar {
      padding: 12px;
      border-bottom: 1px solid var(--panel-border);
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .filter-block {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .filter-block-title {
      font-size: 12px;
      font-weight: 700;
      color: var(--text);
    }

    .filter-label {
      font-size: 12px;
      font-weight: 600;
      color: var(--muted);
    }

    .filter-control {
      width: 100%;
      min-height: 36px;
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      background: #fff;
      color: var(--text);
      padding: 0 10px;
      font-size: 13px;
    }

    .button-filter {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .filter-pill {
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      background: #fff;
      color: var(--text);
      cursor: pointer;
      min-height: 32px;
      padding: 0 10px;
      font-size: 12px;
      font-weight: 600;
    }

    .filter-pill.active {
      background: var(--accent-soft);
      border-color: var(--accent);
      color: #115e59;
    }

    .text-list {
      overflow: auto;
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .text-button {
      text-align: left;
      padding: 10px 12px;
      font-size: 13px;
      line-height: 1.35;
    }

    .load-more-button {
      text-align: center;
      font-weight: 600;
    }

    .load-more-button:disabled {
      cursor: progress;
      color: var(--muted);
      background: #f9fafb;
    }

    .panel-body {
      min-height: 0;
      overflow: auto;
      padding: 14px;
    }

    .text-view {
      height: 100%;
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 13px;
      line-height: 1.55;
      word-break: break-word;
    }

    .text-highlight {
      background: #fef3c7;
      border-radius: 4px;
      padding: 1px 0;
      transition: background-color 120ms ease, box-shadow 120ms ease;
    }

    .text-highlight.active {
      background: #fde68a;
      box-shadow: inset 0 0 0 1px var(--active);
    }

    .text-highlight.deep-active {
      background: #facc15;
      box-shadow: inset 0 0 0 1px #b45309;
    }

    .item-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .item-card {
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      padding: 12px;
      background: #fff;
      transition: border-color 120ms ease, background-color 120ms ease;
    }

    .item-card.active {
      border-color: var(--active);
      background: #fffbeb;
    }

    .item-card.unmatched {
      border-style: dashed;
    }

    .item-title {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: flex-start;
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 8px;
    }

    .item-badge {
      color: var(--muted);
      font-size: 11px;
      white-space: nowrap;
    }

    .field-row {
      display: grid;
      grid-template-columns: 112px minmax(0, 1fr);
      gap: 10px;
      font-size: 12px;
      line-height: 1.45;
      padding: 3px 0;
    }

    .field-label {
      color: var(--muted);
      font-weight: 600;
    }

    .field-value {
      min-width: 0;
      word-break: break-word;
    }

    .field-row.related-active .field-label,
    .field-row.related-active .field-value {
      color: #92400e;
      font-weight: 700;
    }

    .empty-state {
      height: 100%;
      display: grid;
      place-items: center;
      text-align: center;
      color: var(--muted);
      padding: 24px;
      font-size: 14px;
      line-height: 1.5;
    }

    .hidden { display: none; }

    @media (max-width: 1200px) {
      .app-shell { grid-template-columns: 240px minmax(0, 1fr) 320px; }
    }
  </style>
</head>
<body>
  <div class="app-shell">
    <aside class="panel">
      <div class="group-bar" id="groupBar"></div>
      <div class="filter-bar">
        <div id="filterBlocks"></div>
      </div>
      <div class="text-list" id="textList"></div>
    </aside>

    <main class="panel">
      <div class="panel-header" id="mainHeader">Text</div>
      <div class="panel-body" id="mainPanel"></div>
    </main>

    <section class="panel">
      <div class="panel-header" id="detailHeader">Extracted Items</div>
      <div class="panel-body" id="detailPanel"></div>
    </section>
  </div>

  <script>
    const state = {
      groups: [],
      texts: [],
      activeGroup: null,
      activeTextId: null,
      hoveredItemId: null,
      hoveredFieldKeys: [],
      filtersByScope: {},
      offset: 0,
      total: 0,
      hasMore: false,
      isLoading: false,
      error: null,
      requestId: 0,
    };

    async function loadData() {
      const data = await fetchJson('/api/groups', 'Failed to load extraction groups from server');
      state.groups = data.groups || [];
      initializeSelection();
      await loadTexts(true);
    }

    async function fetchJson(url, message) {
      const response = await fetch(url);
      let data = null;
      try {
        data = await response.json();
      } catch (error) {
        throw new Error(message);
      }
      if (!response.ok) {
        throw new Error((data && data.error) || message);
      }
      return data;
    }

    function initializeSelection() {
      const group = state.groups.find((entry) => entry.total > 0) || state.groups[0] || null;
      state.activeGroup = group ? group.key : null;
    }

    function getActiveGroup() {
      return state.groups.find((group) => group.key === state.activeGroup) || null;
    }

    function getActiveText() {
      if (!state.activeTextId) return null;
      return state.texts.find((text) => text.text_id === state.activeTextId) || null;
    }

    function buildTextsUrl() {
      const params = new URLSearchParams({
        group: state.activeGroup,
        offset: String(state.offset),
        limit: '1000',
      });
      const activeFilters = {};
      for (const [scope, filters] of Object.entries(state.filtersByScope)) {
        const scopeFilters = {};
        for (const [column, value] of Object.entries(filters || {})) {
          if (value && value !== 'all') {
            scopeFilters[column] = value;
          }
        }
        if (Object.keys(scopeFilters).length > 0) {
          activeFilters[scope] = scopeFilters;
        }
      }
      if (Object.keys(activeFilters).length > 0) {
        params.set('filters', JSON.stringify(activeFilters));
      }
      return `/api/texts?${params.toString()}`;
    }

    async function loadTexts(reset) {
      if (!state.activeGroup) {
        state.texts = [];
        state.activeTextId = null;
        render();
        return;
      }

      if (reset) {
        state.texts = [];
        state.activeTextId = null;
        state.offset = 0;
        state.total = 0;
        state.hasMore = false;
      }

      const requestId = state.requestId + 1;
      state.requestId = requestId;
      state.isLoading = true;
      state.error = null;
      render();

      try {
        const data = await fetchJson(buildTextsUrl(), 'Failed to load texts from server');
        if (requestId !== state.requestId) return;
        state.texts = reset ? data.texts : state.texts.concat(data.texts);
        state.offset = data.offset + data.texts.length;
        state.total = data.total;
        state.hasMore = data.has_more;
        ensureValidActiveText();
      } catch (error) {
        if (requestId !== state.requestId) return;
        state.error = error.message || 'Failed to load texts from server';
      } finally {
        if (requestId === state.requestId) {
          state.isLoading = false;
          render();
        }
      }
    }

    function ensureValidActiveText() {
      if (!state.texts.some((text) => text.text_id === state.activeTextId)) {
        state.activeTextId = state.texts[0] ? state.texts[0].text_id : null;
      }
    }

    function render() {
      renderGroups();
      renderFilterBlocks();
      renderTextList();
      renderMainPanel();
      renderDetailPanel();
      syncHoverState();
    }

    function renderGroups() {
      const groupBar = document.getElementById('groupBar');
      groupBar.innerHTML = '';
      for (const group of state.groups) {
        const button = document.createElement('button');
        button.className = 'group-button' + (group.key === state.activeGroup ? ' active' : '');
        button.textContent = `${group.label} (${group.total})`;
        button.addEventListener('click', () => {
          state.activeGroup = group.key;
          state.filtersByScope = {};
          state.hoveredItemId = null;
          state.hoveredFieldKeys = [];
          loadTexts(true);
        });
        groupBar.appendChild(button);
      }
    }

    function renderFilterBlocks() {
      const container = document.getElementById('filterBlocks');
      const group = getActiveGroup();
      const blocks = group ? (group.filter_blocks || []) : [];
      container.innerHTML = '';
      container.classList.toggle('hidden', blocks.length === 0);

      for (const block of blocks) {
        const wrapper = document.createElement('div');
        wrapper.className = 'filter-block';
        wrapper.innerHTML = `<div class="filter-block-title">${escapeHtml(block.label)}</div>`;
        for (const filter of block.filters || []) {
          wrapper.appendChild(renderFilterControl(block.scope, filter));
        }
        container.appendChild(wrapper);
      }
    }

    function renderFilterControl(scope, filter) {
      const id = `filter-${scope}-${filter.column}`;
      const value = getFilterValue(scope, filter.column);
      const wrapper = document.createElement('div');
      if (filter.method === 'dropdown') {
        wrapper.innerHTML = `
          <label class="filter-label" for="${escapeHtml(id)}">${escapeHtml(filter.label)}</label>
          <select class="filter-control" id="${escapeHtml(id)}">
            <option value="all">All</option>
            ${(filter.values || []).map((entry) => `<option value="${escapeHtml(entry)}">${escapeHtml(entry)}</option>`).join('')}
          </select>
        `;
        const select = wrapper.querySelector('select');
        select.value = value || 'all';
        select.addEventListener('change', (event) => setFilterValue(scope, filter.column, event.target.value));
        return wrapper;
      }
      if (filter.method === 'button') {
        wrapper.innerHTML = `
          <div class="filter-label">${escapeHtml(filter.label)}</div>
          <div class="button-filter">
            <button class="filter-pill" type="button" data-value="all">All</button>
            ${(filter.values || []).map((entry) => `<button class="filter-pill" type="button" data-value="${escapeHtml(entry)}">${escapeHtml(entry)}</button>`).join('')}
          </div>
        `;
        wrapper.querySelectorAll('.filter-pill').forEach((button) => {
          button.classList.toggle('active', (value || 'all') === button.dataset.value);
          button.addEventListener('click', () => setFilterValue(scope, filter.column, button.dataset.value || 'all'));
        });
        return wrapper;
      }
      const placeholder = filter.method === 'multitext' ? 'value-1,value-2' : 'Search text';
      wrapper.innerHTML = `
        <label class="filter-label" for="${escapeHtml(id)}">${escapeHtml(filter.label)}</label>
        <input class="filter-control" id="${escapeHtml(id)}" type="text" value="${escapeHtml(value || '')}" placeholder="${escapeHtml(placeholder)}">
      `;
      const input = wrapper.querySelector('input');
      input.addEventListener('input', (event) => setFilterValue(scope, filter.column, event.target.value));
      return wrapper;
    }

    function getFilterValue(scope, column) {
      return (state.filtersByScope[scope] || {})[column] || '';
    }

    function setFilterValue(scope, column, value) {
      state.filtersByScope[scope] = Object.assign({}, state.filtersByScope[scope] || {}, { [column]: value });
      if (!value || value === 'all') {
        delete state.filtersByScope[scope][column];
      }
      if (Object.keys(state.filtersByScope[scope] || {}).length === 0) {
        delete state.filtersByScope[scope];
      }
      state.hoveredItemId = null;
      state.hoveredFieldKeys = [];
      loadTexts(true);
    }

    function renderTextList() {
      const textList = document.getElementById('textList');
      textList.innerHTML = '';
      if (state.error) {
        textList.innerHTML = `<div class="empty-state">${escapeHtml(state.error)}</div>`;
        return;
      }
      if (state.isLoading && state.texts.length === 0) {
        textList.innerHTML = '<div class="empty-state">Loading texts...</div>';
        return;
      }
      if (state.texts.length === 0) {
        textList.innerHTML = '<div class="empty-state">No texts match the selected filters.</div>';
        return;
      }

      for (const text of state.texts) {
        const button = document.createElement('button');
        button.className = 'text-button' + (text.text_id === state.activeTextId ? ' active' : '');
        button.innerHTML = `<strong>${escapeHtml(text.title)}</strong><br><span>${text.items.length} items</span>`;
        button.addEventListener('click', () => {
          state.activeTextId = text.text_id;
          state.hoveredItemId = null;
          state.hoveredFieldKeys = [];
          render();
        });
        textList.appendChild(button);
      }

      if (state.hasMore) {
        const button = document.createElement('button');
        button.className = 'text-button load-more-button';
        button.disabled = state.isLoading;
        button.textContent = state.isLoading ? 'Loading...' : `Load more (${state.texts.length} of ${state.total})`;
        button.addEventListener('click', () => loadTexts(false));
        textList.appendChild(button);
      }
    }

    function renderMainPanel() {
      const mainHeader = document.getElementById('mainHeader');
      const mainPanel = document.getElementById('mainPanel');
      const text = getActiveText();

      if (!text) {
        mainHeader.textContent = 'Text';
        mainPanel.innerHTML = '<div class="empty-state">Select a text to review its extracted highlights.</div>';
        return;
      }

      mainHeader.textContent = text.title;
      mainPanel.innerHTML = `<div class="text-view">${text.highlighted_html}</div>`;

      mainPanel.querySelectorAll('.text-highlight').forEach((element) => {
        element.addEventListener('mouseenter', () => {
          const itemIds = (element.dataset.itemIds || '').split(',').filter(Boolean);
          const relatedFields = (element.dataset.relatedFields || '').split(',').filter(Boolean);
          state.hoveredItemId = itemIds[0] || null;
          state.hoveredFieldKeys = relatedFields;
          syncHoverState();
        });
        element.addEventListener('mouseleave', () => {
          state.hoveredItemId = null;
          state.hoveredFieldKeys = [];
          syncHoverState();
        });
      });
    }

    function renderDetailPanel() {
      const detailHeader = document.getElementById('detailHeader');
      const detailPanel = document.getElementById('detailPanel');
      const text = getActiveText();
      const items = text ? text.items : [];

      if (!text) {
        detailHeader.textContent = 'Extracted Items';
        detailPanel.innerHTML = '<div class="empty-state">No extracted items to display.</div>';
        return;
      }

      detailHeader.textContent = `Extracted Items (${items.length})`;
      if (items.length === 0) {
        detailPanel.innerHTML = '<div class="empty-state">This text has no extracted items for the selected filters.</div>';
        return;
      }

      const cards = items.map((item, index) => {
        const fields = item.fields.map((field) => `
          <div class="field-row" data-item-id="${escapeHtml(item.item_id)}" data-field-key="${escapeHtml(field.key)}">
            <div class="field-label">${escapeHtml(field.label)}</div>
            <div class="field-value">${escapeHtml(String(field.value))}</div>
          </div>
        `).join('');
        const matchBadge = item.has_match ? 'linked to text' : 'no exact text match';
        const unmatchedClass = item.has_match ? '' : ' unmatched';

        return `
          <div class="item-card${unmatchedClass}" data-item-id="${escapeHtml(item.item_id)}">
            <div class="item-title">
              <span>${escapeHtml(item.title || `${item.tag} ${index + 1}`)}</span>
              <span class="item-badge">${escapeHtml(item.tag)} | ${escapeHtml(matchBadge)}</span>
            </div>
            ${fields}
          </div>
        `;
      }).join('');

      detailPanel.innerHTML = `<div class="item-list">${cards}</div>`;
      detailPanel.querySelectorAll('.item-card').forEach((card) => {
        card.addEventListener('mouseenter', () => {
          state.hoveredItemId = card.dataset.itemId;
          state.hoveredFieldKeys = [];
          syncHoverState();
        });
        card.addEventListener('mouseleave', () => {
          state.hoveredItemId = null;
          state.hoveredFieldKeys = [];
          syncHoverState();
        });
      });
      detailPanel.querySelectorAll('.field-row[data-field-key]').forEach((row) => {
        row.addEventListener('mouseenter', () => {
          state.hoveredItemId = row.dataset.itemId;
          state.hoveredFieldKeys = [`${row.dataset.itemId}::${row.dataset.fieldKey}`];
          syncHoverState();
        });
        row.addEventListener('mouseleave', () => {
          state.hoveredItemId = null;
          state.hoveredFieldKeys = [];
          syncHoverState();
        });
      });
    }

    function syncHoverState() {
      document.querySelectorAll('.item-card').forEach((card) => {
        card.classList.toggle('active', state.hoveredItemId && card.dataset.itemId === state.hoveredItemId);
      });
      document.querySelectorAll('.field-row[data-field-key]').forEach((row) => {
        const fieldToken = `${row.dataset.itemId}::${row.dataset.fieldKey}`;
        row.classList.toggle('related-active', state.hoveredFieldKeys.includes(fieldToken));
      });
      document.querySelectorAll('.text-highlight').forEach((highlight) => {
        const itemIds = (highlight.dataset.itemIds || '').split(',').filter(Boolean);
        const relatedFields = (highlight.dataset.relatedFields || '').split(',').filter(Boolean);
        highlight.classList.toggle('active', state.hoveredItemId && itemIds.includes(state.hoveredItemId));
        highlight.classList.toggle(
          'deep-active',
          state.hoveredFieldKeys.some((fieldKey) => relatedFields.includes(fieldKey))
        );
      });
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    loadData().catch((error) => {
      document.body.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
    });
  </script>
</body>
</html>
"""
