const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(
  path.join(__dirname, 'adalove_observer_export.js'),
  'utf8',
);
const context = {
  URL,
  clearTimeout,
  console: { error() {}, log() {}, warn() {} },
  location: { hostname: 'example.invalid' },
  setTimeout,
  window: {},
};

vm.runInNewContext(source, context, { filename: 'adalove_observer_export.js' });

const extract = context.window.adaloveObserverExporter.extractResourceCode;

assert.equal(
  extract('https://integrada.minhabiblioteca.com.br/reader/books/9788582600542/pageid/329'),
  '9788582600542',
);
assert.equal(
  extract('https://integrada.minhabiblioteca.com.br/books/978-85-216-2288-8'),
  '978-85-216-2288-8',
);
assert.equal(
  extract('See https://integrada.minhabiblioteca.com.br/#/books/9786555204087.'),
  '9786555204087',
);
assert.equal(
  extract('https://integrada.minhabiblioteca.com.br/reader/books/978%2D85%2D216%2D2288%2D8'),
  '978-85-216-2288-8',
);
assert.equal(extract('https://example.com/books/9788582600542'), '');
assert.equal(extract('not a URL'), '');

const activitiesColumns = source.match(/const activitiesColumns = \[([\s\S]*?)\n  \];/)[1];
const activityHeaders = [...activitiesColumns.matchAll(/header: '([^']+)'/g)]
  .map(match => match[1]);

assert.deepEqual(activityHeaders.slice(0, 2), ['Activity order', 'Week']);
assert.equal(activityHeaders.includes('Week order'), false);

console.log('adalove_observer_export tests passed');
