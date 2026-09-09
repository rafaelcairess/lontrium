const token = document.querySelector('meta[name="fgc-token"]').content;
const storeGrid = document.querySelector('#storeGrid');
const toast = document.querySelector('#toast');
const supportedLocales = ['en', 'pt-BR', 'es'];
const {normalizeLocale, detectLocale, setupScheduleValues} = window.ClaimerI18n;
const logoStores = new Set(['steam', 'epic', 'gog', 'ubisoft', 'aliexpress', 'shopee']);
const setupSteps = ['Language', 'Stores', 'Security', 'Accounts', 'Schedule', 'Review'];
let translations = {};
let currentLocale = 'en';
let latestStatus = null;
let latestConfig = null;
let latestUpdate = null;
let activeSettingsSection = 'section.stores';
let setupStep = 0;
let setupValues = {};
let setupLoginMode = 'browser';
let setupScheduleMode = 'startup';
let statusPollTimer = null;

function detectedLocale() {
  return detectLocale(
    localStorage.getItem('claimer-control-language'),
    navigator.languages || [navigator.language],
  );
}

function valueAt(key) {
  return key.split('.').reduce((value, part) => value && value[part], translations);
}

function t(key, params = {}) {
  let text = valueAt(key);
  if (typeof text !== 'string') return key;
  for (const [name, value] of Object.entries(params)) {
    text = text.replaceAll(`{${name}}`, String(value));
  }
  return text;
}

async function setLocale(locale, persist = true) {
  currentLocale = normalizeLocale(locale);
  const response = await fetch(`/assets/locales/${currentLocale}.json`, { cache: 'no-store' });
  if (!response.ok) throw new Error('Unable to load language');
  translations = await response.json();
  document.documentElement.lang = currentLocale;
  document.title = t('app.title');
  document.querySelector('#languageSelect').value = currentLocale;
  if (persist) localStorage.setItem('claimer-control-language', currentLocale);
  for (const element of document.querySelectorAll('[data-i18n]')) {
    element.textContent = t(element.dataset.i18n);
  }
  for (const element of document.querySelectorAll('[data-i18n-aria-label]')) {
    element.setAttribute('aria-label', t(element.dataset.i18nAriaLabel));
  }
  if (latestStatus) renderStatus(latestStatus);
  if (latestConfig && document.querySelector('#settingsDrawer').classList.contains('open')) renderSettings(latestConfig);
  if (!document.querySelector('#onboarding').hidden) renderOnboarding();
  renderUpdate();
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {'Content-Type': 'application/json', 'X-FGC-Token': token, ...(options.headers || {})},
  });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.code ? t(data.code) : (data.error || t('error.generic')));
    error.code = data.code;
    throw error;
  }
  return data;
}

function showToast(message, error = false) {
  toast.textContent = message;
  toast.className = `toast show${error ? ' error' : ''}`;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.className = 'toast'; }, 3500);
}

function relativeTime(value) {
  if (!value) return t('common.never');
  const date = new Date(value);
  const seconds = Math.round((date.getTime() - Date.now()) / 1000);
  const formatter = new Intl.RelativeTimeFormat(currentLocale, {numeric: 'auto'});
  for (const [size, unit] of [[86400, 'day'], [3600, 'hour'], [60, 'minute']]) {
    if (Math.abs(seconds) >= size) return formatter.format(Math.round(seconds / size), unit);
  }
  return formatter.format(seconds, 'second');
}

function createStoreIcon(store) {
  const icon = document.createElement('span');
  icon.className = `store-icon store-${store.key}`;
  icon.setAttribute('aria-hidden', 'true');
  if (logoStores.has(store.key)) {
    const logo = document.createElement('span');
    logo.className = `store-logo logo-${store.key}`;
    icon.append(logo);
  } else {
    icon.textContent = store.badge;
  }
  return icon;
}

const outcomeKeys = {
  claimed: 'status.claimed', owned: 'status.owned', available: 'status.available', failed: 'status.failedItem',
  skipped: 'status.skipped', action_required: 'status.actionRequired', processed: 'status.processed',
};

function createStoreDetails(details) {
  if (!details || !details.kind) return null;
  const panel = document.createElement('div');
  panel.className = 'store-results';
  if (details.kind === 'games') {
    const list = document.createElement('ul');
    list.className = 'result-list';
    for (const item of details.items || []) {
      const entry = document.createElement('li');
      const title = document.createElement('span');
      title.className = 'result-title';
      title.textContent = item.title;
      const outcome = document.createElement('span');
      outcome.className = `result-outcome outcome-${item.outcome}`;
      outcome.textContent = t(outcomeKeys[item.outcome] || 'status.processed');
      entry.append(title, outcome);
      list.append(entry);
    }
    panel.append(list);
    return panel;
  }
  if (details.kind === 'coins') {
    const coinKeys = {collected: 'coins.collected', collected_manual: 'coins.collectedManual', already_collected: 'coins.already', not_collected: 'coins.notCollected', available: 'coins.simulation'};
    const outcome = document.createElement('strong');
    outcome.className = `coin-outcome coin-${details.outcome}`;
    outcome.textContent = t(coinKeys[details.outcome] || 'coins.notCollected');
    const metrics = document.createElement('div');
    metrics.className = 'coin-metrics';
    const values = [];
    if (details.claimedCoins !== null && ['collected', 'collected_manual'].includes(details.outcome)) values.push(t('coins.gained', {count: details.claimedCoins}));
    else if (details.offeredCoins !== null) values.push(t('coins.offer', {count: details.offeredCoins}));
    if (details.balance !== null) values.push(t('coins.balance', {count: details.balance}));
    if (details.streakDays !== null) values.push(t(details.streakDays === 1 ? 'coins.streak' : 'coins.streakMany', {count: details.streakDays}));
    if (details.tomorrowCoins !== null) values.push(t('coins.tomorrow', {count: details.tomorrowCoins}));
    for (const value of values) {
      const metric = document.createElement('span');
      metric.textContent = value;
      metrics.append(metric);
    }
    panel.append(outcome, metrics);
    return panel;
  }
  return null;
}

function createStoreRow(store, globalRunning) {
  const row = document.createElement('article');
  row.className = 'store-row';
  row.dataset.state = store.state;
  const identity = document.createElement('div');
  identity.className = 'store-identity';
  const names = document.createElement('div');
  const title = document.createElement('h3');
  title.className = 'store-name';
  title.textContent = store.name;
  const key = document.createElement('p');
  key.className = 'store-key';
  key.textContent = store.authNoteKey ? t(store.authNoteKey) : store.key;
  names.append(title, key);
  identity.append(createStoreIcon(store), names);
  const state = document.createElement('div');
  state.className = 'store-state';
  const marker = document.createElement('span');
  marker.className = 'state-marker';
  const message = document.createElement('span');
  message.textContent = t(store.messageKey || 'status.waiting');
  state.append(marker, message);
  const lastRun = document.createElement('div');
  lastRun.className = 'last-run';
  const lastRunLabel = document.createElement('span');
  lastRunLabel.className = 'last-run-label';
  lastRunLabel.textContent = t('dashboard.lastExecution');
  const lastRunValue = document.createElement('strong');
  lastRunValue.className = 'last-run-value';
  lastRunValue.textContent = store.lastRun ? relativeTime(store.lastRun) : t('dashboard.sessionNever');
  lastRun.append(lastRunLabel, lastRunValue);
  const run = document.createElement('button');
  run.className = 'button run-store';
  run.type = 'button';
  run.textContent = t(store.state === 'running' ? 'status.runningButton' : 'status.run');
  const storeBusy = store.state === 'queued' || store.state === 'running';
  run.disabled = storeBusy || (globalRunning && store.key !== 'shopee');
  run.addEventListener('click', () => runStores([store.key]));
  row.append(identity, state, lastRun, run);
  const details = createStoreDetails(store.details);
  if (details) row.append(details);
  return row;
}

function createAddStoreRow(availableCount) {
  const button = document.createElement('button');
  button.className = 'add-store-row';
  button.id = 'addStoreButton';
  button.type = 'button';
  const symbol = document.createElement('span');
  symbol.className = 'add-symbol';
  symbol.textContent = '+';
  symbol.setAttribute('aria-hidden', 'true');
  const copy = document.createElement('span');
  copy.className = 'add-copy';
  const title = document.createElement('strong');
  title.textContent = t(availableCount ? 'store.add' : 'store.manage');
  const detail = document.createElement('small');
  detail.textContent = availableCount ? t(availableCount === 1 ? 'store.availableOne' : 'store.availableMany', {count: availableCount}) : t('store.allActive');
  copy.append(title, detail);
  button.append(symbol, copy);
  button.addEventListener('click', openStoreManager);
  return button;
}

function renderHistory(status) {
  const container = document.querySelector('#historyList');
  const records = Array.isArray(status.history) ? status.history.slice(0, 50) : [];
  const stores = new Map(status.stores.map(store => [store.key, store]));
  if (!records.length) {
    const empty = document.createElement('p');
    empty.className = 'history-empty';
    empty.textContent = t('history.empty');
    container.replaceChildren(empty);
    return;
  }
  const cards = records.map(record => {
    const store = stores.get(record.store) || {key: record.store, name: record.store, badge: '?'};
    const card = document.createElement('article');
    card.className = 'history-card';
    card.dataset.state = record.state;
    const header = document.createElement('div');
    header.className = 'history-card-header';
    const identity = document.createElement('div');
    identity.className = 'store-identity';
    const name = document.createElement('strong');
    name.className = 'history-store-name';
    name.textContent = store.name;
    identity.append(createStoreIcon(store), name);
    const summary = document.createElement('div');
    summary.className = 'history-summary';
    const message = document.createElement('strong');
    message.textContent = t(record.messageKey || 'status.completedNoChanges');
    const timestamp = document.createElement('time');
    timestamp.dateTime = record.finishedAt || '';
    timestamp.textContent = relativeTime(record.finishedAt);
    summary.append(message, timestamp);
    header.append(identity, summary);
    card.append(header);
    const details = createStoreDetails(record.details);
    if (details) {
      details.classList.add('history-details');
      card.append(details);
    }
    return card;
  });
  container.replaceChildren(...cards);
}

function renderStatus(status) {
  latestStatus = status;
  const enabledStores = status.stores.filter(store => store.enabled);
  storeGrid.replaceChildren(...enabledStores.map(store => createStoreRow(store, status.running)), createAddStoreRow(status.stores.length - enabledStores.length));
  document.querySelector('#activeStoreCount').textContent = String(enabledStores.length);
  document.querySelector('#lastRun').textContent = relativeTime(status.finishedAt);
  document.querySelector('#nextRun').textContent = status.schedule.nextRun ? relativeTime(status.schedule.nextRun) : t('dashboard.manualOnly');
  document.querySelector('#runLabel').textContent = t(status.running ? 'dashboard.running' : 'dashboard.ready');
  document.querySelector('#runPill').classList.toggle('running', status.running);
  document.querySelector('#runAllButton').disabled = status.running || enabledStores.length === 0;
  renderHistory(status);
}

async function refreshStatus(silent = true) {
  try { renderStatus(await api('/api/status')); }
  catch (error) { if (!silent) showToast(error.message, true); }
}

function statusPollDelay() {
  if (document.hidden) return 30000;
  return latestStatus?.running ? 2000 : 15000;
}

function scheduleStatusPoll(delay = statusPollDelay()) {
  clearTimeout(statusPollTimer);
  statusPollTimer = setTimeout(async () => {
    await refreshStatus();
    scheduleStatusPoll();
  }, delay);
}

async function runStores(stores = null) {
  try {
    await api('/api/run', {method: 'POST', body: JSON.stringify({stores})});
    showToast(t(stores ? 'store.runStarted' : 'store.allStarted'));
    await refreshStatus();
  } catch (error) { showToast(error.message, true); }
}

function renderStoreChoices(container, name, selected) {
  const rows = latestStatus.stores.map(store => {
    const label = document.createElement('label');
    label.className = 'store-picker-row';
    const copy = document.createElement('span');
    copy.className = 'store-picker-name';
    const storeName = document.createElement('span');
    storeName.textContent = store.name;
    copy.append(storeName);
    if (store.authNoteKey) {
      const note = document.createElement('small');
      note.textContent = t(store.authNoteKey);
      copy.append(note);
    }
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.name = name;
    input.value = store.key;
    input.checked = selected.includes(store.key);
    label.append(createStoreIcon(store), copy, input);
    return label;
  });
  container.replaceChildren(...rows);
}

function renderStoreManager() {
  renderStoreChoices(document.querySelector('#storeManagerList'), 'stores', latestStatus.stores.filter(store => store.enabled).map(store => store.key));
}

async function openStoreManager() {
  try {
    if (!latestStatus) await refreshStatus(false);
    renderStoreManager();
    document.querySelector('#storeModalBackdrop').hidden = false;
    document.querySelector('#storeManagerList input')?.focus();
  } catch (error) { showToast(error.message, true); }
}

function closeStoreManager() { document.querySelector('#storeModalBackdrop').hidden = true; }

async function saveStoreSelection(event) {
  event.preventDefault();
  const stores = new FormData(event.currentTarget).getAll('stores');
  if (stores.length === 0) return showToast(t('store.selectOne'), true);
  try {
    await api('/api/config', {method: 'POST', body: JSON.stringify({values: {STORES: stores}})});
    closeStoreManager();
    showToast(t('store.updated'));
    await refreshStatus();
  } catch (error) { showToast(error.message, true); }
}

function createTooltip(key, id) {
  const group = document.createElement('span');
  group.className = 'help-group';
  const button = document.createElement('button');
  button.className = 'help-button';
  button.type = 'button';
  button.textContent = '?';
  button.setAttribute('aria-describedby', id);
  button.setAttribute('aria-expanded', 'false');
  const tooltip = document.createElement('span');
  tooltip.className = 'help-tooltip';
  tooltip.id = id;
  tooltip.role = 'tooltip';
  tooltip.textContent = t(key);
  button.addEventListener('click', () => {
    const open = group.classList.toggle('open');
    button.setAttribute('aria-expanded', String(open));
  });
  group.append(button, tooltip);
  return group;
}

function createInput(spec, current, configured, prefix = '') {
  const wrapper = document.createElement('div');
  wrapper.className = spec.kind === 'boolean' ? 'check-row' : 'field';
  const input = document.createElement('input');
  input.name = `${prefix}${spec.key}`;
  input.dataset.settingKey = spec.key;
  if (spec.kind === 'boolean') {
    input.type = 'checkbox';
    input.checked = Boolean(current);
    const label = document.createElement('label');
    label.textContent = t(spec.labelKey);
    wrapper.append(input, label);
    return wrapper;
  }
  input.type = spec.kind === 'integer' ? 'number' : (spec.secret ? 'password' : 'text');
  if (!spec.secret && current !== null && current !== undefined) input.value = current;
  if (spec.min !== null) input.min = spec.min;
  if (spec.max !== null) input.max = spec.max;
  input.placeholder = spec.secret && configured ? `•••••• ${t('common.configured')}` : (spec.helpKey ? t(spec.helpKey) : '');
  const label = document.createElement('label');
  const labelText = document.createElement('span');
  labelText.textContent = t(spec.labelKey);
  label.append(labelText);
  if (spec.credentialPurposeKey) label.append(createTooltip(spec.credentialPurposeKey, `help-${prefix}${spec.key}`));
  if (spec.secret && configured) {
    const marker = document.createElement('span');
    marker.className = 'configured';
    marker.textContent = '✓';
    label.append(marker);
  }
  wrapper.append(label, input);
  if (spec.helpKey) {
    const help = document.createElement('small');
    help.textContent = t(spec.helpKey);
    wrapper.append(help);
  }
  return wrapper;
}

function createSettingsPanel(sectionKey, body) {
  const panel = document.createElement('section');
  panel.className = 'settings-panel';
  panel.dataset.section = sectionKey;
  const header = document.createElement('header');
  header.className = 'settings-panel-header';
  const title = document.createElement('h3');
  title.textContent = t(sectionKey);
  const description = document.createElement('p');
  description.textContent = t(sectionKey.replace('section.', 'sectionDescription.'));
  header.append(title, description);
  panel.append(header, body);
  return panel;
}

function activateSettingsSection(name) {
  activeSettingsSection = name;
  for (const panel of document.querySelectorAll('.settings-panel')) panel.hidden = panel.dataset.section !== name;
  for (const button of document.querySelectorAll('.settings-nav-item')) {
    const active = button.dataset.section === name;
    button.classList.toggle('active', active);
    button.setAttribute('aria-current', active ? 'page' : 'false');
  }
}

function renderSettings(config) {
  latestConfig = config;
  const options = document.createElement('div');
  options.className = 'store-settings-list';
  renderStoreChoices(options, 'STORES', config.values.STORES);
  const panels = [createSettingsPanel('section.stores', options)];
  const sections = new Map();
  for (const spec of config.schema.filter(item => item.key !== 'STORES')) {
    if (!sections.has(spec.sectionKey)) sections.set(spec.sectionKey, []);
    sections.get(spec.sectionKey).push(spec);
  }
  for (const [sectionKey, specs] of sections) {
    const grid = document.createElement('div');
    grid.className = 'field-grid';
    for (const spec of specs) grid.append(createInput(spec, config.values[spec.key], config.configured[spec.key]));
    panels.push(createSettingsPanel(sectionKey, grid));
  }
  document.querySelector('#settingsContent').replaceChildren(...panels);
  const navItems = panels.map(panel => {
    const button = document.createElement('button');
    button.className = 'settings-nav-item';
    button.type = 'button';
    button.dataset.section = panel.dataset.section;
    const key = panel.dataset.section.replace('section.', '');
    const store = latestStatus?.stores.find(item => item.key === key);
    if (store) {
      button.append(createStoreIcon(store));
    } else {
      const icon = document.createElement('span');
      icon.className = 'settings-nav-symbol';
      icon.setAttribute('aria-hidden', 'true');
      icon.textContent = {stores: '▦', schedule: '◷', browser: '◎', notifications: '◇'}[key] || '·';
      button.append(icon);
    }
    const label = document.createElement('span');
    label.textContent = t(panel.dataset.section);
    button.append(label);
    button.addEventListener('click', () => activateSettingsSection(panel.dataset.section));
    return button;
  });
  document.querySelector('#settingsNav').replaceChildren(...navItems);
  if (!panels.some(panel => panel.dataset.section === activeSettingsSection)) activeSettingsSection = 'section.stores';
  activateSettingsSection(activeSettingsSection);
}

async function openSettings() {
  try {
    if (!latestStatus) await refreshStatus(false);
    renderSettings(await api('/api/config'));
    document.querySelector('#drawerBackdrop').hidden = false;
    document.querySelector('#settingsDrawer').classList.add('open');
    document.querySelector('#settingsDrawer').setAttribute('aria-hidden', 'false');
  } catch (error) { showToast(error.message, true); }
}

function closeSettings() {
  document.querySelector('#settingsDrawer').classList.remove('open');
  document.querySelector('#settingsDrawer').setAttribute('aria-hidden', 'true');
  setTimeout(() => { document.querySelector('#drawerBackdrop').hidden = true; }, 180);
}

function valuesFromForm(form, schema, prefix = '') {
  const formData = new FormData(form);
  const values = {};
  for (const spec of schema) {
    if (spec.kind === 'stores') values[spec.key] = formData.getAll(`${prefix}${spec.key}`);
    else {
      const input = form.querySelector(`[data-setting-key="${spec.key}"]`);
      if (input) values[spec.key] = spec.kind === 'boolean' ? input.checked : input.value;
    }
  }
  return values;
}

async function saveSettings(event) {
  event.preventDefault();
  try {
    const values = valuesFromForm(event.currentTarget, latestConfig.schema);
    const result = await api('/api/config', {method: 'POST', body: JSON.stringify({values})});
    showToast(t('settings.saved', {count: result.changed.length}));
    closeSettings();
    await refreshStatus();
  } catch (error) { showToast(error.message, true); }
}

function setupSelectedStores() { return Array.isArray(setupValues.STORES) ? setupValues.STORES : []; }

function captureSetupStep() {
  const form = document.querySelector('#onboardingForm');
  for (const input of form.querySelectorAll('[data-setting-key]')) {
    if (input.type === 'checkbox' && input.dataset.settingKey === 'STORES') continue;
    setupValues[input.dataset.settingKey] = input.type === 'checkbox' ? input.checked : input.value;
  }
  const stores = [...form.querySelectorAll('input[data-setting-key="STORES"]:checked')].map(input => input.value);
  if (form.querySelector('input[data-setting-key="STORES"]')) setupValues.STORES = stores;
  const loginMode = form.querySelector('input[name="setup-login-mode"]:checked');
  if (loginMode) setupLoginMode = loginMode.value;
  const scheduleMode = form.querySelector('input[name="setup-schedule-mode"]:checked');
  if (scheduleMode) {
    setupScheduleMode = scheduleMode.value;
    const dailyTime = form.querySelector('#setup-daily-time')?.value || '12:00';
    Object.assign(setupValues, setupScheduleValues(setupScheduleMode, dailyTime));
  }
}

function setupChoice(name, value, titleKey, copyKey, selected, badgeKey = '') {
  const label = document.createElement('label');
  label.className = `setup-choice${selected ? ' selected' : ''}`;
  const input = document.createElement('input');
  input.type = 'radio';
  input.name = name;
  input.value = value;
  input.checked = selected;
  const copy = document.createElement('span');
  const heading = document.createElement('strong');
  heading.textContent = t(titleKey);
  if (badgeKey) {
    const badge = document.createElement('small');
    badge.className = 'setup-choice-badge';
    badge.textContent = t(badgeKey);
    heading.append(badge);
  }
  const description = document.createElement('span');
  description.textContent = t(copyKey);
  copy.append(heading, description);
  label.append(input, copy);
  input.addEventListener('change', () => {
    for (const choice of label.parentElement.querySelectorAll('.setup-choice')) choice.classList.toggle('selected', choice.querySelector('input').checked);
  });
  return label;
}

function setupHeader(titleKey, copyKey) {
  const header = document.createElement('header');
  header.className = 'setup-page-header';
  const title = document.createElement('h2');
  title.textContent = t(titleKey);
  const copy = document.createElement('p');
  copy.textContent = t(copyKey);
  header.append(title, copy);
  return header;
}

function setupLanguagePage() {
  const page = document.createElement('section');
  page.append(setupHeader('onboarding.languageTitle', 'onboarding.languageCopy'));
  const choices = document.createElement('div');
  choices.className = 'language-cards';
  for (const [locale, label] of [['en', 'English'], ['pt-BR', 'Português do Brasil'], ['es', 'Español']]) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `language-card${currentLocale === locale ? ' selected' : ''}`;
    button.textContent = label;
    button.addEventListener('click', () => setLocale(locale));
    choices.append(button);
  }
  page.append(choices);
  return page;
}

function setupSecurityPage() {
  const page = document.createElement('section');
  page.append(setupHeader('onboarding.loginTitle', 'onboarding.loginCopy'));
  const choices = document.createElement('div');
  choices.className = 'setup-choice-list';
  const credentialsAvailable = selectedCredentialSpecs().length > 0;
  if (!credentialsAvailable) setupLoginMode = 'browser';
  choices.append(setupChoice('setup-login-mode', 'browser', 'onboarding.browserLoginTitle', 'onboarding.browserLoginCopy', setupLoginMode === 'browser', 'onboarding.recommended'));
  if (credentialsAvailable) choices.append(setupChoice('setup-login-mode', 'credentials', 'onboarding.credentialsLoginTitle', 'onboarding.credentialsLoginCopy', setupLoginMode === 'credentials'));
  page.append(choices);
  const card = document.createElement('div');
  card.className = 'security-detail-card';
  for (const key of ['security.title', 'security.summary', 'security.notEncrypted']) {
    const paragraph = document.createElement(key === 'security.title' ? 'h3' : 'p');
    paragraph.textContent = t(key);
    card.append(paragraph);
  }
  if (setupSelectedStores().includes('shopee')) {
    const note = document.createElement('p');
    note.className = 'setup-important';
    note.textContent = t('storeAuth.shopee');
    card.append(note);
  }
  page.append(card);
  return page;
}

function setupStoresPage() {
  const page = document.createElement('section');
  page.append(setupHeader('onboarding.storesTitle', 'onboarding.storesCopy'));
  const choices = document.createElement('div');
  choices.className = 'store-picker setup-store-picker';
  renderStoreChoices(choices, 'setup-STORES', setupSelectedStores());
  for (const input of choices.querySelectorAll('input')) input.dataset.settingKey = 'STORES';
  page.append(choices);
  return page;
}

function credentialSectionKeys() {
  const stores = new Set(setupSelectedStores());
  const sections = new Set([...stores].map(store => `section.${store}`));
  if (stores.has('fab')) sections.add('section.epic');
  if (stores.has('gamerpower')) {
    sections.add('section.fanatical');
    sections.add('section.itchio');
    sections.add('section.indiegala');
  }
  return sections;
}

function selectedCredentialSpecs() {
  const sections = credentialSectionKeys();
  return latestConfig.schema.filter(spec => spec.credentialPurposeKey && sections.has(spec.sectionKey));
}

function setupAccountsPage() {
  const page = document.createElement('section');
  page.append(setupHeader('onboarding.accountsTitle', 'onboarding.accountsCopy'));
  if (setupLoginMode === 'browser') {
    const card = document.createElement('div');
    card.className = 'setup-plan-card';
    const title = document.createElement('h3');
    title.textContent = t('onboarding.manualPlanTitle');
    const copy = document.createElement('p');
    copy.textContent = t('onboarding.manualPlanCopy');
    const stores = document.createElement('p');
    stores.className = 'setup-plan-stores';
    stores.textContent = setupSelectedStores().map(key => latestStatus.stores.find(store => store.key === key)?.name || key).join(' · ');
    card.append(title, copy, stores);
    page.append(card);
    return page;
  }
  const specs = selectedCredentialSpecs();
  const grid = document.createElement('div');
  grid.className = 'field-grid setup-fields';
  for (const spec of specs) {
    const field = createInput(spec, '', latestConfig.configured[spec.key], 'setup-');
    const input = field.querySelector('input');
    if (input && setupValues[spec.key]) input.value = setupValues[spec.key];
    grid.append(field);
  }
  page.append(grid);
  return page;
}

function setupSchedulePage() {
  const page = document.createElement('section');
  page.append(setupHeader('onboarding.scheduleTitle', 'onboarding.scheduleCopy'));
  const choices = document.createElement('div');
  choices.className = 'setup-choice-list';
  choices.append(
    setupChoice('setup-schedule-mode', 'startup', 'onboarding.scheduleStartupTitle', 'onboarding.scheduleStartupCopy', setupScheduleMode === 'startup', 'onboarding.recommended'),
    setupChoice('setup-schedule-mode', 'daily', 'onboarding.scheduleDailyTitle', 'onboarding.scheduleDailyCopy', setupScheduleMode === 'daily'),
    setupChoice('setup-schedule-mode', 'manual', 'onboarding.scheduleManualTitle', 'onboarding.scheduleManualCopy', setupScheduleMode === 'manual'),
  );
  const timeField = document.createElement('label');
  timeField.className = 'setup-time-field';
  const timeLabel = document.createElement('span');
  timeLabel.textContent = t('onboarding.dailyTime');
  const time = document.createElement('input');
  time.type = 'time';
  time.id = 'setup-daily-time';
  time.value = String(setupValues.SCHEDULER_FIXED_TIMES || '12:00').split(',')[0];
  timeField.append(timeLabel, time);
  const timezone = document.createElement('p');
  timezone.className = 'setup-timezone';
  timezone.textContent = t('onboarding.timezone', {timezone: setupValues.SCHEDULER_TIMEZONE});
  const syncTimeState = () => {
    const selected = choices.querySelector('input[name="setup-schedule-mode"]:checked')?.value;
    time.disabled = selected === 'manual';
    timeField.classList.toggle('disabled', time.disabled);
  };
  for (const input of choices.querySelectorAll('input')) input.addEventListener('change', syncTimeState);
  syncTimeState();
  page.append(choices, timeField, timezone);
  return page;
}

function setupReviewPage() {
  const page = document.createElement('section');
  page.append(setupHeader('onboarding.reviewTitle', 'onboarding.reviewCopy'));
  const review = document.createElement('dl');
  review.className = 'setup-review';
  const selected = setupSelectedStores();
  const entered = Object.entries(setupValues).filter(([key, value]) => latestConfig.schema.some(spec => spec.key === key && spec.secret) && value).length;
  const rows = [
    [t('onboarding.selectedStores'), selected.map(key => latestStatus.stores.find(store => store.key === key)?.name || key).join(', ')],
    [t('onboarding.loginMethod'), t(setupLoginMode === 'browser' ? 'onboarding.browserLoginTitle' : 'onboarding.credentialsLoginTitle')],
    [t('onboarding.credentialsConfigured'), setupLoginMode === 'browser' ? t('onboarding.noneStoredNow') : String(entered)],
    [t('onboarding.automation'), t(`onboarding.schedule${setupScheduleMode[0].toUpperCase()}${setupScheduleMode.slice(1)}Title`)],
    [t('security.title'), t('onboarding.localOnly')],
    [t('onboarding.nextStep'), t(setupLoginMode === 'browser' ? 'onboarding.nextManualLogin' : 'onboarding.nextRun')],
  ];
  for (const [term, description] of rows) {
    const group = document.createElement('div');
    const dt = document.createElement('dt');
    dt.textContent = term;
    const dd = document.createElement('dd');
    dd.textContent = description;
    group.append(dt, dd);
    review.append(group);
  }
  page.append(review);
  return page;
}

function renderOnboarding() {
  const steps = setupSteps.map((name, index) => {
    const item = document.createElement('li');
    item.className = index === setupStep ? 'active' : (index < setupStep ? 'complete' : '');
    const number = document.createElement('span');
    number.textContent = index < setupStep ? '✓' : String(index + 1);
    const label = document.createElement('span');
    label.textContent = t(`onboarding.step${name}`);
    item.append(number, label);
    return item;
  });
  document.querySelector('#onboardingSteps').replaceChildren(...steps);
  const factories = [setupLanguagePage, setupStoresPage, setupSecurityPage, setupAccountsPage, setupSchedulePage, setupReviewPage];
  const content = document.querySelector('#onboardingContent');
  content.replaceChildren(factories[setupStep]());
  content.scrollTo({top: 0, left: 0});
  document.querySelector('#setupBack').hidden = setupStep === 0;
  document.querySelector('#setupNext').textContent = t(setupStep === setupSteps.length - 1 ? 'onboarding.finish' : 'common.continue');
}

async function nextSetupStep() {
  captureSetupStep();
  if (setupStep === 1 && setupSelectedStores().length === 0) return showToast(t('store.selectOne'), true);
  if (setupStep < setupSteps.length - 1) {
    setupStep += 1;
    renderOnboarding();
    return;
  }
  try {
    await api('/api/setup', {method: 'POST', body: JSON.stringify({values: setupValues})});
    document.querySelector('#onboarding').hidden = true;
    await refreshStatus(false);
    await runStores();
  } catch (error) { showToast(error.message, true); }
}

function previousSetupStep() {
  captureSetupStep();
  setupStep = Math.max(0, setupStep - 1);
  renderOnboarding();
}

function renderUpdate() {
  const banner = document.querySelector('#updateBanner');
  if (!latestUpdate?.available) {
    banner.hidden = true;
    return;
  }
  document.querySelector('#updateMessage').textContent = t('update.available', {version: latestUpdate.latestVersion});
  banner.hidden = false;
}

async function checkUpdate() {
  try { latestUpdate = await api('/api/update'); renderUpdate(); }
  catch (_) { /* Updates never block local claiming. */ }
}

function launchUpdater() {
  if (!latestUpdate?.available) return;
  if (window.confirm(t('update.confirm', {version: latestUpdate.latestVersion}))) {
    if (/Windows/i.test(navigator.userAgent)) {
      window.location.href = 'lontrium://update';
    } else if (latestUpdate.releaseUrl) {
      window.open(latestUpdate.releaseUrl, '_blank', 'noopener');
    }
  }
}

async function initialise() {
  await setLocale(detectedLocale(), false);
  latestStatus = await api('/api/status');
  latestConfig = await api('/api/config');
  setupValues = {...latestConfig.values, STORES: [...latestConfig.values.STORES]};
  if (!setupValues.RUN_ON_STARTUP && !setupValues.SCHEDULER_FIXED_TIMES && Number(setupValues.SCHEDULER_HOURS) === 0) setupScheduleMode = 'manual';
  else if (!setupValues.RUN_ON_STARTUP) setupScheduleMode = 'daily';
  renderStatus(latestStatus);
  if (latestConfig.setup.required && !latestConfig.setup.complete) {
    document.querySelector('#onboarding').hidden = false;
    renderOnboarding();
  }
  checkUpdate();
}

document.querySelector('#vncLink').href = `${location.protocol}//${location.hostname}:7080/?autoconnect=true`;
document.querySelector('#languageSelect').addEventListener('change', event => setLocale(event.target.value));
document.querySelector('#runAllButton').addEventListener('click', () => runStores());
document.querySelector('#refreshButton').addEventListener('click', () => refreshStatus(false));
document.querySelector('#settingsButton').addEventListener('click', openSettings);
document.querySelector('#closeSettings').addEventListener('click', closeSettings);
document.querySelector('#drawerBackdrop').addEventListener('click', closeSettings);
document.querySelector('#settingsForm').addEventListener('submit', saveSettings);
document.querySelector('#closeStoreModal').addEventListener('click', closeStoreManager);
document.querySelector('#cancelStoreModal').addEventListener('click', closeStoreManager);
document.querySelector('#storeModalBackdrop').addEventListener('click', event => { if (event.target.id === 'storeModalBackdrop') closeStoreManager(); });
document.querySelector('#storeManagerForm').addEventListener('submit', saveStoreSelection);
document.querySelector('#setupBack').addEventListener('click', previousSetupStep);
document.querySelector('#setupNext').addEventListener('click', nextSetupStep);
document.querySelector('#updateButton').addEventListener('click', launchUpdater);
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && document.querySelector('#onboarding').hidden) { closeStoreManager(); closeSettings(); }
});
document.addEventListener('click', event => {
  if (!event.target.closest('.help-group')) {
    for (const group of document.querySelectorAll('.help-group.open')) group.classList.remove('open');
  }
});

initialise()
  .catch(error => showToast(error.message || t('error.generic'), true))
  .finally(() => scheduleStatusPoll());
document.addEventListener('visibilitychange', () => scheduleStatusPoll(document.hidden ? 30000 : 0));
