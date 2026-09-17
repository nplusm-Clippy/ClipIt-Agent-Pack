import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import path from 'node:path'
import test from 'node:test'
import vm from 'node:vm'
import { webcrypto } from 'node:crypto'

const require = createRequire(process.env.CLIPIT_TEST_NODE_MODULES ? path.join(process.env.CLIPIT_TEST_NODE_MODULES, 'package.json') : import.meta.url)
const React = require('react')
const { JSDOM } = require('jsdom')
const source = await readFile(new URL('../desktop/plugin.js', import.meta.url), 'utf8')

test('Control Room renders all five views and submits the exact displayed approval', async () => {
  const dom = new JSDOM('<div id="root"></div>', { url: 'https://hermes.local/' })
  globalThis.window = dom.window; globalThis.document = dom.window.document
  const originalNavigator = Object.getOwnPropertyDescriptor(globalThis, 'navigator')
  Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true })
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  const { createRoot } = require('react-dom/client')
  const { act } = React
  const calls = [], contributions = [], disposers = [], saved = new Map()
  saved.set(`receipt:test:${'a'.repeat(64)}:user-1:key-1`, { version: 1, operation: 'import_url', idempotencyKey: 'original-import-key', pending: false, runId: 'import-job' })
  const host = { state: { profile: { get: () => 'test', subscribe: () => () => {} } }, notify() {}, navigate() {} }
  const approval = { approvalId: 'approval-1', tasks: [{ title: 'Export the selected edit', parameters: { exportId: 'export-1' } }], totalEstimatedCost: 3, expiresAt: '2099-01-01T00:00:00.000Z', actionDigest: 'd'.repeat(64), decisions: ['approved', 'cancelled'] }
  const ctx = { i18n: { register() {} }, storage: { get: (k, f) => saved.get(k) || f, set: (k, v) => saved.set(k, v) }, os: { notify() {}, openExternal() {} },
    onDispose: fn => disposers.push(fn), registerMany: values => contributions.push(...values),
    async rest(route, options) {
      calls.push({ route, options })
      if (route === '/status') return { connected: true, connectionId: 'a'.repeat(64), accountId: 'user-1', credentialId: 'key-1', scope: { enterprise: false }, permissions: { clippy_agent: true }, compatibility: { contractVersion: '2026-09-16', features: { coordinatedPolling: false } } }
      if (route === '/doctor') return { pluginVersion: '3.0.0', connection: { connected: true } }
      if (route === '/operations/overview') return { credits: { balanceClip: 20 }, runs: [], approvals: [] }
      if (route === '/operations/job') return { id: 'import-job', status: 'completed', result: { videoId: 'restored-video' } }
      if (route === '/operations/runs') return { items: [{ id: 'run-1', name: 'My reviewed edit', status: 'awaiting_approval' }], page: {} }
      if (route === '/operations/run') return { id: 'run-1', name: 'My reviewed edit', status: 'awaiting_approval', progress: 40, currentApproval: approval, steps: [], allowedControls: [] }
      if (route === '/operations/catalog') return { items: [{ name: 'futureCapability', description: 'Create a test draft', available: true, parameters: { type: 'object', properties: { title: { type: 'string' } } } }] }
      if (route === '/operations/approval') return { operationId: 'operation-1', runId: 'continuation-1', status: 'completed' }
      return { items: [], page: {} }
    }
  }
  const sdk = { host, useValue: atom => atom.get(), usePluginI18n: () => key => ({ overview: 'Overview', runs: 'Runs', library: 'Library', capabilities: 'Capabilities', settings: 'Settings', refresh: 'Refresh', source: 'Start with your source', doctor: 'Run Doctor' })[key] || key,
    Button: props => React.createElement('button', props), Input: props => React.createElement('input', props), Textarea: props => React.createElement('textarea', props),
    ROUTES_AREA: 'routes', SIDEBAR_NAV_AREA: 'sidebar', STATUSBAR_AREAS: { right: 'status' }, PALETTE_AREA: 'palette', PANES_AREA: 'panes', COMPOSER_AREAS: { attachments: 'attachments' } }
  const context = vm.createContext({ console, URL, crypto: webcrypto, window: dom.window, document: dom.window.document, AbortController, setTimeout, clearTimeout, fetch: () => { throw new Error('Unexpected media request') } })
  const modules = Object.fromEntries(Object.entries({ react: React, '@hermes/plugin-sdk': sdk }).map(([name, exports]) => [name,
    new vm.SyntheticModule(Object.keys(exports), function () { for (const [key, value] of Object.entries(exports)) this.setExport(key, value) }, { context })]))
  const module = new vm.SourceTextModule(source, { context })
  await module.link(name => modules[name]); await module.evaluate(); module.namespace.default.register(ctx)
  const root = createRoot(document.getElementById('root'))
  const settle = () => new Promise(resolve => setImmediate(resolve))
  const click = async label => {
    const target = [...document.querySelectorAll('button')].find(button => button.textContent === label)
    assert.ok(target, `Button '${label}' exists`)
    await act(async () => { target.click(); await settle() })
  }
  try {
    await act(async () => { root.render(contributions.find(c => c.area === 'routes').render()); await settle() })
    assert.match(document.body.textContent, /Start with your source/)
    await click('Check imported video')
    assert.equal(document.querySelector('input').value, 'restored-video')
    for (const label of ['Runs', 'Library', 'Capabilities', 'Settings', 'Overview']) {
      await click(label)
      assert.equal(document.querySelector('button[aria-current="page"]').textContent, label)
    }
    await click('Runs'); await click('My reviewed edit')
    assert.match(document.body.textContent, /Export the selected edit/)
    const approve = [...document.querySelectorAll('button')].find(b => b.textContent === 'Approve actions')
    assert.equal(approve.disabled, true)
    await act(async () => { document.querySelector('input[type="checkbox"]').click(); await settle() })
    await click('Approve actions')
    const submitted = calls.find(call => call.route === '/operations/approval').options.body
    assert.equal(submitted.id, 'run-1')
    assert.equal(submitted.body.approvalId, 'approval-1')
    assert.equal(submitted.body.actionDigest, approval.actionDigest)
    assert.equal(submitted.body.decision, 'approved')
    assert.ok(submitted.body.idempotencyKey)
    assert.equal(submitted.connectionId, 'a'.repeat(64))
    assert.ok(calls.some(call => call.route === '/operations/run' && call.options.body.id === 'continuation-1'))
    await click('Settings'); await click('Run Doctor')
    assert.match(document.body.textContent, /3.0.0/)
    assert.ok(!document.body.innerHTML.includes('test-secret'))
  } finally {
    await act(async () => root.unmount())
    for (const dispose of disposers) dispose()
    dom.window.close()
    delete globalThis.window; delete globalThis.document; delete globalThis.IS_REACT_ACT_ENVIRONMENT
    if (originalNavigator) Object.defineProperty(globalThis, 'navigator', originalNavigator)
    else delete globalThis.navigator
  }
})
