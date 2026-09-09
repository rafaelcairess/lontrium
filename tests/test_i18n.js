const test = require('node:test');
const assert = require('node:assert/strict');
const {normalizeLocale, detectLocale, setupScheduleValues} = require('../src/gui/static/i18n.js');

test('normalizes Portuguese and Spanish Windows locales', () => {
  assert.equal(normalizeLocale('pt-PT'), 'pt-BR');
  assert.equal(normalizeLocale('pt-BR'), 'pt-BR');
  assert.equal(normalizeLocale('es-MX'), 'es');
  assert.equal(normalizeLocale('fr-FR'), 'en');
});

test('saved preference wins over browser languages', () => {
  assert.equal(detectLocale('es', ['pt-BR', 'en-US']), 'es');
});

test('browser language is used when there is no saved preference', () => {
  assert.equal(detectLocale(null, ['pt-BR', 'en-US']), 'pt-BR');
  assert.equal(detectLocale(null, ['es-AR', 'en-US']), 'es');
  assert.equal(detectLocale(null, ['de-DE']), 'en');
});

test('setup schedule presets map to validated backend settings', () => {
  assert.deepEqual(setupScheduleValues('startup', '08:30'), {
    SCHEDULER_HOURS: 0, SCHEDULER_FIXED_TIMES: '08:30', RUN_ON_STARTUP: true,
  });
  assert.deepEqual(setupScheduleValues('daily', '21:15'), {
    SCHEDULER_HOURS: 0, SCHEDULER_FIXED_TIMES: '21:15', RUN_ON_STARTUP: false,
  });
  assert.deepEqual(setupScheduleValues('manual', '09:00'), {
    SCHEDULER_HOURS: 0, SCHEDULER_FIXED_TIMES: '', RUN_ON_STARTUP: false,
  });
  assert.equal(setupScheduleValues('invalid', '99:99').SCHEDULER_FIXED_TIMES, '12:00');
});
