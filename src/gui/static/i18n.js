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

  function setupScheduleValues(mode, dailyTime = '12:00') {
    const safeMode = ['startup', 'daily', 'manual'].includes(mode) ? mode : 'startup';
    const safeTime = /^([01]\d|2[0-3]):[0-5]\d$/.test(String(dailyTime)) ? String(dailyTime) : '12:00';
    return {
      SCHEDULER_HOURS: 0,
      SCHEDULER_FIXED_TIMES: safeMode === 'manual' ? '' : safeTime,
      RUN_ON_STARTUP: safeMode === 'startup',
    };
  }

  const api = {normalizeLocale, detectLocale, setupScheduleValues};
  root.ClaimerI18n = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
}(typeof window === 'undefined' ? globalThis : window));
