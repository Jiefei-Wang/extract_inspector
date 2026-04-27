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
      gap: 6px;
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

    .highlight-lines {
      display: flex;
      flex-direction: column;
      gap: 3px;
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
        <div id="categoricalFilters"></div>
        <label class="filter-label" for="textIdFilter">Text ID</label>
        <input class="filter-control" id="textIdFilter" type="text" placeholder="text-001,text-002">
        <div id="subjectFilterBlock">
          <label class="filter-label" for="subjectIdFilter">Subject ID</label>
          <input class="filter-control" id="subjectIdFilter" type="text" placeholder="subject-001,subject-002">
        </div>
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
      categoricalFilters: {},
      textIdFilter: '',
      subjectIdFilter: '',
      hasSubjectId: false,
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
      state.hasSubjectId = Boolean(data.has_subject_id);
      bindControls();
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

    function bindControls() {
      const textIdFilter = document.getElementById('textIdFilter');
      textIdFilter.value = state.textIdFilter;
      textIdFilter.addEventListener('input', (event) => {
        state.textIdFilter = event.target.value;
        state.hoveredItemId = null;
        loadTexts(true);
      });

      const subjectBlock = document.getElementById('subjectFilterBlock');
      subjectBlock.classList.toggle('hidden', !state.hasSubjectId);
      const subjectIdFilter = document.getElementById('subjectIdFilter');
      subjectIdFilter.value = state.subjectIdFilter;
      subjectIdFilter.addEventListener('input', (event) => {
        state.subjectIdFilter = event.target.value;
        state.hoveredItemId = null;
        loadTexts(true);
      });
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
      for (const [column, value] of Object.entries(state.categoricalFilters)) {
        if (value && value !== 'all') {
          activeFilters[column] = value;
        }
      }
      if (Object.keys(activeFilters).length > 0) {
        params.set('filters', JSON.stringify(activeFilters));
      }
      if (state.textIdFilter.trim()) {
        params.set('text_ids', state.textIdFilter);
      }
      if (state.hasSubjectId && state.subjectIdFilter.trim()) {
        params.set('subject_ids', state.subjectIdFilter);
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
      renderCategoricalFilters();
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
          state.categoricalFilters = {};
          state.hoveredItemId = null;
          loadTexts(true);
        });
        groupBar.appendChild(button);
      }
    }

    function renderCategoricalFilters() {
      const container = document.getElementById('categoricalFilters');
      const group = getActiveGroup();
      const filters = group ? (group.filters || []) : [];
      container.innerHTML = '';
      container.classList.toggle('hidden', filters.length === 0);

      for (const filter of filters) {
        const id = `filter-${filter.column}`;
        const wrapper = document.createElement('div');
        wrapper.innerHTML = `
          <label class="filter-label" for="${escapeHtml(id)}">${escapeHtml(filter.label)}</label>
          <select class="filter-control" id="${escapeHtml(id)}">
            <option value="all">All</option>
            ${(filter.values || []).map((value) => {
              return `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`;
            }).join('')}
          </select>
        `;
        const select = wrapper.querySelector('select');
        select.value = state.categoricalFilters[filter.column] || 'all';
        select.addEventListener('change', (event) => {
          state.categoricalFilters[filter.column] = event.target.value;
          state.hoveredItemId = null;
          loadTexts(true);
        });
        container.appendChild(wrapper);
      }
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
        const subject = text.subject_id ? ` | Subject ${escapeHtml(text.subject_id)}` : '';
        button.className = 'text-button' + (text.text_id === state.activeTextId ? ' active' : '');
        button.innerHTML = `<strong>Text ${escapeHtml(text.text_id)}${subject}</strong><br><span>${text.items.length} items</span>`;
        button.addEventListener('click', () => {
          state.activeTextId = text.text_id;
          state.hoveredItemId = null;
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

      const subject = text.subject_id ? ` | Subject ${text.subject_id}` : '';
      mainHeader.textContent = `Text ${text.text_id}${subject}`;
      mainPanel.innerHTML = `<div class="text-view">${text.highlighted_html}</div>`;

      mainPanel.querySelectorAll('.text-highlight').forEach((element) => {
        element.addEventListener('mouseenter', () => {
          const itemIds = (element.dataset.itemIds || '').split(',').filter(Boolean);
          state.hoveredItemId = itemIds[0] || null;
          syncHoverState();
        });
        element.addEventListener('mouseleave', () => {
          state.hoveredItemId = null;
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
          <div class="field-row">
            <div class="field-label">${escapeHtml(field.label)}</div>
            <div class="field-value">${escapeHtml(String(field.value))}</div>
          </div>
        `).join('');
        const highlightLines = [];
        Object.entries(item.highlights_by_column || {}).forEach(([column, values]) => {
          (values || []).forEach((value) => {
            highlightLines.push(`(${column}) ${value}`);
          });
        });
        if (highlightLines.length === 0) {
          (item.highlights || []).forEach((value) => {
            highlightLines.push(value);
          });
        }
        (item.spans || []).forEach((span) => {
          highlightLines.push(`(${span.start}, ${span.end}) ${span.text}`);
        });
        const highlights = highlightLines.length ? `
          <div class="field-row">
            <div class="field-label">Highlight</div>
            <div class="field-value highlight-lines">
              ${highlightLines.map((line) => `<div>${escapeHtml(line)}</div>`).join('')}
            </div>
          </div>
        ` : '';
        const matchBadge = item.has_match ? 'linked to text' : 'no exact text match';
        const unmatchedClass = item.has_match ? '' : ' unmatched';

        return `
          <div class="item-card${unmatchedClass}" data-item-id="${escapeHtml(item.item_id)}">
            <div class="item-title">
              <span>${escapeHtml(`${item.summary} ${index + 1}`)}</span>
              <span class="item-badge">${escapeHtml(matchBadge)}</span>
            </div>
            ${highlights}
            ${fields}
          </div>
        `;
      }).join('');

      detailPanel.innerHTML = `<div class="item-list">${cards}</div>`;
      detailPanel.querySelectorAll('.item-card').forEach((card) => {
        card.addEventListener('mouseenter', () => {
          state.hoveredItemId = card.dataset.itemId;
          syncHoverState();
        });
        card.addEventListener('mouseleave', () => {
          state.hoveredItemId = null;
          syncHoverState();
        });
      });
    }

    function syncHoverState() {
      document.querySelectorAll('.item-card').forEach((card) => {
        card.classList.toggle('active', state.hoveredItemId && card.dataset.itemId === state.hoveredItemId);
      });
      document.querySelectorAll('.text-highlight').forEach((highlight) => {
        const itemIds = (highlight.dataset.itemIds || '').split(',').filter(Boolean);
        highlight.classList.toggle('active', state.hoveredItemId && itemIds.includes(state.hoveredItemId));
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
