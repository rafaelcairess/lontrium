(function exposeClaimerI18n(root) {
  function normalizeLocale(value) {
    const locale = String(value || '').toLowerCase();
    if (locale.startsWith('pt')) return 'pt-BR';
    if (locale.startsWith('es')) return 'es';
    return 'en';
  }

  function detectLocale(saved, languages = []) {
    const supported = new Set(['en', 'pt-BR', 'es']);
    if (supported.has(saved)) return saved;
    for (const language of languages) {
      const normalized = normalizeLocale(language);
      if (supported.has(normalized) && normalized !== 'en') return normalized;
      if (String(language || '').toLowerCase().startsWith('en')) return 'en';
    }
    return 'en';
  }

  function setupScheduleValues(mode, dailyTimes = '12:00,16:00,19:00') {
    const candidate = ({startup: 'economy', daily: 'economy'})[mode] || mode;
    const safeMode = ['economy', 'dashboard', 'manual'].includes(candidate) ? candidate : 'economy';
    const parts = String(dailyTimes).split(',').map(value => value.trim());
    const safeTimes = parts.length > 0 && parts.every(value => /^([01]\d|2[0-3]):[0-5]\d$/.test(value))
      ? [...new Set(parts)].join(',') : '12:00,16:00,19:00';
    return {
      SCHEDULER_HOURS: 0,
      SCHEDULER_FIXED_TIMES: safeMode === 'economy' ? safeTimes : '',
      RUN_ON_STARTUP: safeMode === 'dashboard',
      WINDOWS_ECONOMY_SCHEDULE: safeMode === 'economy',
    };
  }

  const api = {normalizeLocale, detectLocale, setupScheduleValues};
  root.ClaimerI18n = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
}(typeof window === 'undefined' ? globalThis : window));
