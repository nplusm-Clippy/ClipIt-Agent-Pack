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
  saved.set('control-room-mode:test', 'classic')
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

async function modernFixture(handler) {
  const dom = new JSDOM('<div id="root"></div>', { url: 'https://hermes.local/' })
  globalThis.window = dom.window; globalThis.document = dom.window.document
  const originalNavigator = Object.getOwnPropertyDescriptor(globalThis, 'navigator')
  Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true })
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  dom.window.HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); this.querySelector('button')?.focus() }
  dom.window.HTMLDialogElement.prototype.close = function () { this.removeAttribute('open') }
  const { createRoot } = require('react-dom/client'), { act } = React
  const calls = [], contributions = [], disposers = [], saved = new Map(), external = [], listeners = new Set()
  let profile = 'qa'
  const host = { state: { profile: { get: () => profile, subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn) } } }, notify() {}, navigate() {} }
  const status = { connected: true, connectionId: 'a'.repeat(64), appOrigin: 'https://staging.clipit.test', accountId: 'private-account-id', credentialId: 'private-key-id', accountLabel: 'Fieldwork Studio', credentialLabel: 'Editorial QA', scope: { workspaceName: 'Fieldwork Studio', enterprise: true }, permissions: { clippy_agent: true, video_processing: true, clip_generation: true }, compatibility: { contractVersion: '2026-09-16', features: { coordinatedPolling: false, workflowPresentation: true, resourceSearch: true } } }
  const ctx = { i18n: { register() {} }, storage: { get: (key, fallback) => saved.has(key) ? saved.get(key) : fallback, set: (key, value) => saved.set(key, value) }, os: { openExternal: value => external.push(value) },
    onDispose: fn => disposers.push(fn), registerMany: values => contributions.push(...values),
    async rest(route, options) { calls.push({ route, options }); if (route === '/status') return { ...status, credentialId: `${profile}-credential` }; return await handler(route, options) || { items: [], page: {} } }
  }
  const sdk = { host, useValue: atom => atom.get(), usePluginI18n: () => key => key,
    Button: props => React.createElement('button', props), Input: props => React.createElement('input', props), Textarea: props => React.createElement('textarea', props),
    ROUTES_AREA: 'routes', SIDEBAR_NAV_AREA: 'sidebar', STATUSBAR_AREAS: { right: 'status' }, PALETTE_AREA: 'palette', PANES_AREA: 'panes', COMPOSER_AREAS: { attachments: 'attachments' } }
  const context = vm.createContext({ console, URL, crypto: webcrypto, window: dom.window, document: dom.window.document, AbortController, setTimeout, clearTimeout, TextEncoder, fetch: () => { throw new Error('Unexpected media request') } })
  const modules = Object.fromEntries(Object.entries({ react: React, '@hermes/plugin-sdk': sdk }).map(([name, exports]) => [name,
    new vm.SyntheticModule(Object.keys(exports), function () { for (const [key, value] of Object.entries(exports)) this.setExport(key, value) }, { context })]))
  const module = new vm.SourceTextModule(source, { context }); await module.link(name => modules[name]); await module.evaluate(); module.namespace.default.register(ctx)
  const root = createRoot(document.getElementById('root')), settle = () => new Promise(resolve => setImmediate(resolve))
  await act(async () => { root.render(contributions.find(c => c.area === 'routes').render()); await settle() })
  return { calls, contributions, saved, external, dom, status,
    text() { const clone = document.querySelector('main').cloneNode(true); clone.querySelectorAll('style, details').forEach(node => node.remove()); return clone.textContent },
    async click(label, within = document) { const target = [...within.querySelectorAll('button')].find(button => button.textContent === label || button.getAttribute('aria-label') === label); assert.ok(target, `Button '${label}' exists`); assert.equal(target.disabled, false, `${label} enabled`); await act(async () => { target.focus(); target.click(); await settle() }); return target },
    async selectTask() { const target = document.querySelector('.cr-task'); assert.ok(target); await act(async () => { target.click(); await settle() }) },
    async input(element, value) { await act(async () => { const type = element.tagName === 'TEXTAREA' ? dom.window.HTMLTextAreaElement : element.tagName === 'SELECT' ? dom.window.HTMLSelectElement : dom.window.HTMLInputElement; Object.getOwnPropertyDescriptor(type.prototype, 'value').set.call(element, value); element.dispatchEvent(new dom.window.Event(element.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })); await settle() }) },
    async changeProfile(value) { await act(async () => { profile = value; listeners.forEach(fn => fn()); await settle() }) },
    async close() { await act(async () => root.unmount()); disposers.forEach(fn => fn()); dom.window.close(); delete globalThis.window; delete globalThis.document; delete globalThis.IS_REACT_ACT_ENVIRONMENT; if (originalNavigator) Object.defineProperty(globalThis, 'navigator', originalNavigator); else delete globalThis.navigator }
  }
}

test('modern Activity uses names, verifies fresh approval, preserves exact target and follows continuation', async () => {
  const approval = { approvalId: 'approval-secret-id', actionDigest: 'd'.repeat(64), tasks: [{ title: 'Export launch overview', prompt: 'Keep the first phrase', parameters: { format: 'mp4', height: 1920 }, estimatedCost: 2.4 }], totalEstimatedCost: 2.4, expiresAt: '2099-01-01T00:00:00Z' }
  const run = { id: 'private-run-id', name: 'Prepare launch clips', status: 'awaiting_approval', currentApproval: approval, allowedControls: [], presentation: { source: { label: 'Launch walkthrough', durationSeconds: 760 }, phase: 'Waiting for approval', actorLabel: 'ClipIt workflow' } }
  const f = await modernFixture((route, options) => {
    if (route === '/operations/runs') return { items: [run] }
    if (route === '/operations/run') return options.body.id === 'next-private-id' ? { ...run, id: 'next-private-id', status: 'running', currentApproval: null } : run
    if (route === '/operations/approval') return { status: 'completed', runId: 'next-private-id' }
    if (route === '/operations/events') return { items: [{ sequence: 1, message: 'Draft clips prepared', occurredAt: '2026-09-17T01:00:00Z' }] }
  })
  try {
    assert.match(f.text(), /Fieldwork Studio/); assert.doesNotMatch(f.text(), /private-account-id|private-key-id|private-run-id/)
    assert.match(document.querySelector('.clipit-control-room style').textContent, /\.clipit-control-room dialog\{margin:auto;/)
    assert.equal(f.calls.filter(call => /catalog|recipes|tool$/.test(call.route)).length, 0)
    await f.selectTask(); assert.match(f.text(), /Launch walkthrough · 12:40/); assert.doesNotMatch(f.text(), /40%/)
    const trigger = await f.click('Review proposed actions')
    assert.match(document.querySelector('dialog').textContent, /Keep the first phrase/)
    assert.equal([...document.querySelectorAll('button')].find(b => b.textContent === 'Approve 1 action').disabled, true)
    await React.act(async () => document.querySelector('dialog input[type=checkbox]').click())
    await f.click('Approve 1 action')
    const write = f.calls.find(call => call.route === '/operations/approval')
    assert.equal(write.options.body.body.actionDigest, approval.actionDigest)
    assert.equal(write.options.body.body.approvalId, approval.approvalId)
    assert.equal(write.options.body.id, run.id)
    const writeIndex = f.calls.indexOf(write); assert.equal(f.calls[writeIndex - 1].route, '/operations/run')
    assert.ok(f.calls.some(call => call.route === '/operations/run' && call.options.body.id === 'next-private-id'))
    assert.equal(document.querySelector('dialog'), null)
    assert.ok(document.activeElement === trigger || document.activeElement.tagName === 'H2')
  } finally { await f.close() }
})

test('Outputs excludes unknown associations and loads only the explicitly chosen verified export', async () => {
  const output = { id: 'artifact-one', kind: 'clip', resourceId: 'internal-clip', presentation: { role: 'output', label: 'Opening hook', readiness: 'ready_for_review', appUrl: '/editor?clip=internal-clip' } }
  let stale = false
  const exportValue = { exportId: 'exact-export', format: 'mp4', width: 1080, height: 1920, editorVersion: 3, exactlyMatchesEditor: true, inspectionStatus: 'verified', blockers: [] }
  const f = await modernFixture(route => {
    if (route === '/operations/library') return { items: [output, { id: 'unknown', kind: 'clip', presentation: { role: 'unknown', label: 'Not an output' } }] }
    if (route === '/operations/delivery_state') return { guidance: 'Call applyClipFitAndRender with a canonical snapshot.', selection: { selectedExportId: 'exact-export' }, selectedExport: { ...exportValue, exactlyMatchesEditor: !stale }, exports: [exportValue] }
    if (route === '/operations/download') return { exportId: 'exact-export', downloadUrl: 'https://signed.example.test/export', expiresAt: '2099-01-01T00:00:00Z' }
  })
  try {
    await f.click('Outputs')
    assert.match(f.text(), /Opening hook/); assert.doesNotMatch(f.text(), /Not an output/)
    assert.equal(f.calls.find(call => call.route === '/operations/library').options.body.query.role, 'output')
    await React.act(async () => { document.querySelector('.cr-output').click(); await new Promise(resolve => setImmediate(resolve)) })
    assert.equal(document.querySelector('video'), null)
    assert.equal(f.calls.filter(call => /download|delivery_state/.test(call.route)).length, 0)
    await f.click('Inspect available exports')
    const ordinary = document.querySelector('dialog').cloneNode(true); ordinary.querySelectorAll('details').forEach(node => node.remove())
    assert.doesNotMatch(ordinary.textContent, /applyClipFitAndRender|canonical snapshot/)
    assert.match(document.querySelector('dialog details').textContent, /applyClipFitAndRender/)
    assert.match(document.querySelector('dialog select').textContent, /1080 × 1920/)
    assert.doesNotMatch(document.querySelector('dialog select').textContent, /exact-export/)
    await f.click('Preview exact export')
    assert.equal(document.querySelector('video').getAttribute('src'), 'https://signed.example.test/export')
    assert.equal(f.calls.find(call => call.route === '/operations/download').options.body.query.exportId, 'exact-export')
    stale = true
    await f.click('Download exact export')
    assert.match(document.querySelector('dialog').textContent, /not verified against the current edit/)
    assert.equal(f.calls.filter(call => call.route === '/operations/download').length, 1)
    assert.equal(f.external.length, 0)
    await f.click('Close Opening hook'); assert.equal(document.querySelector('video'), null)
  } finally { await f.close() }
})

test('named brief needs review, uses exact source, and change draft never sends automatically', async () => {
  const run = { id: 'run-new', name: 'Three launch clips', status: 'running', allowedControls: [], presentation: { source: { label: 'Launch walkthrough' } } }
  const f = await modernFixture(route => {
    if (route === '/operations/resources') return { items: [{ id: 'source-private-id', kind: 'video', label: 'Launch walkthrough', status: 'completed', durationSeconds: 760 }] }
    if (route === '/operations/orchestrate') return { status: 'running', runId: run.id }
    if (route === '/operations/run') return run
  })
  try {
    await f.click('New brief'); await f.click('Prepare short clips')
    const select = [...document.querySelectorAll('dialog select')].find(select => select.textContent.includes('Launch walkthrough'))
    await f.input(select, 'source-private-id')
    assert.equal(f.calls.filter(call => call.route === '/operations/orchestrate').length, 0)
    await f.click('Review brief'); assert.match(document.querySelector('dialog').textContent, /Source: Launch walkthrough/)
    await f.click('Start workflow')
    const write = f.calls.find(call => call.route === '/operations/orchestrate').options.body.body
    assert.equal(write.request.videoId, 'source-private-id'); assert.equal(write.request.autoConfirmCostlyTools, false)
    assert.ok(write.idempotencyKey)
    await f.click('Ask for a change'); await f.click('Use in composer attachment')
    const attachment = f.contributions.find(c => c.area === 'attachments'); let attached
    await React.act(async () => { attachment.data.run({ insertText: value => { attached = value } }); await new Promise(resolve => setImmediate(resolve)) })
    assert.match(attached, /Three launch clips/); assert.match(attached, /Internal task reference: run-new/)
    assert.match(document.querySelector('dialog').textContent, /not sent automatically/)
    await f.changeProfile('other')
    assert.equal(document.querySelector('dialog'), null)
    attached = null; await React.act(async () => { attachment.data.run({ insertText: value => { attached = value } }); await new Promise(resolve => setImmediate(resolve)) }); assert.equal(attached, null)
  } finally { await f.close() }
})

test('modern view exposes degraded reads and exact parameters without historical reasoning or approval protocol noise', async () => {
  const approval = { approvalId: 'decision', actionDigest: 'digest', expiresAt: '2099-01-01T00:00:00Z', totalEstimatedCost: 2,
    tasks: [{ id: 'task', title: 'Prepare the reviewed cut', prompt: 'Keep this exact phrase', confirmation: { tool: 'startExport', planId: 'internal-plan-id', planSignature: 'internal-signature', params: { format: 'mp4', width: 1080 } } }] }
  const run = { id: 'run', name: 'Reviewed launch edit', status: 'awaiting_approval', currentApproval: approval, presentation: { latestActivity: { kind: 'progress', message: 'private old summary' } } }
  const f = await modernFixture(route => {
    if (route === '/operations/overview') return { status: 'degraded', degraded: ['credits'], runs: [] }
    if (route === '/operations/runs') return { items: [run] }
    if (route === '/operations/run') return run
    if (route === '/operations/events') return { items: [{ sequence: 1, type: 'progress', message: 'private historical reasoning' }, { sequence: 2, type: 'progress', message: 'unsafe legacy text', presentation: { message: 'Export plan prepared.', actorLabel: 'ClipIt workflow' } }] }
  })
  try {
    assert.match(f.text(), /Some information is unavailable/)
    await f.selectTask(); assert.match(f.text(), /Detailed history is unavailable/); assert.match(f.text(), /Export plan prepared/)
    assert.doesNotMatch(f.text(), /private historical reasoning|unsafe legacy text|private old summary/)
    await f.click('Review proposed actions')
    assert.match(f.text(), /Tool: Start Export/); assert.match(f.text(), /Keep this exact phrase/); assert.match(f.text(), /1080/); assert.match(f.text(), /mp4/)
    assert.doesNotMatch(f.text(), /internal-plan-id|internal-signature/)
    assert.match(document.querySelector('dialog details').textContent, /internal-plan-id/)
  } finally { await f.close() }
})

test('Outputs groups resource identity by newest association while retaining distinct same-name resources', async () => {
  const output = { kind: 'clip', resourceId: 'clip-one', presentation: { role: 'output', label: 'Opening highlight', readiness: 'draft', durationSeconds: 15 } }
  const values = [
    { ...output, id: 'older', createdAt: '2026-09-17 05:00:00' },
    { ...output, id: 'newer', createdAt: '2026-09-17 06:00:00', presentation: { ...output.presentation, sourceLabel: 'Newest association' } },
    { ...output, id: 'other-clip', resourceId: 'clip-two', createdAt: '2026-09-17T07:00:00Z', presentation: { ...output.presentation, durationSeconds: 30 } },
    { ...output, id: 'other-kind', kind: 'video', createdAt: '2026-09-17T08:00:00Z' },
    { id: 'unknown', kind: 'clip', presentation: { role: 'unknown', label: 'Unavailable reference' } }
  ]
  const run = { id: 'run', name: 'Prepared highlights', status: 'completed' }
  const f = await modernFixture(route => {
    if (route === '/operations/library') return { items: values }
    if (route === '/operations/runs') return { items: [run] }
    if (route === '/operations/run') return run
    if (route === '/operations/artifacts') return { items: values }
  })
  try {
    await f.click('Outputs')
    assert.equal(document.querySelectorAll('.cr-output').length, 3)
    assert.match(f.text(), /Newest association/); assert.match(f.text(), /0:15/); assert.match(f.text(), /0:30/); assert.match(f.text(), /Associated/)
    assert.match(f.text(), /Some associated resources are unavailable to this connection or have no confirmed output role/)
    await React.act(async () => { document.querySelector('.cr-output').click(); await new Promise(resolve => setImmediate(resolve)) })
    assert.match(document.querySelector('dialog details').textContent, /"id": "newer"/)
    await f.click('Close Opening highlight')
    await f.click('Activity'); await f.selectTask()
    assert.equal(document.querySelectorAll('.cr-detail .cr-output').length, 4, 'workflow associations stay intact')
    const headings = [...document.querySelectorAll('.cr-detail h3')].map(node => node.textContent)
    assert.ok(headings.indexOf('Outputs') < headings.indexOf('Activity'))
  } finally { await f.close() }
})

test('SQL UTC timestamps match explicit offsets in a non-UTC timezone and event creation time is usable', async () => {
  const originalTZ = process.env.TZ
  process.env.TZ = 'America/Chicago'
  let f
  try {
    const expected = new Date('2026-09-17T05:39:00Z').toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
    const run = { id: 'run', name: 'Finished at midnight', status: 'completed', updatedAt: '2026-09-17 05:39:00.000000' }
    f = await modernFixture(route => {
      if (route === '/operations/runs') return { items: [run] }
      if (route === '/operations/run') return run
      if (route === '/operations/events') return { items: [
        { sequence: 1, type: 'status_changed', occurredAt: '2026-09-17T00:39:00-05:00' },
        { sequence: 2, type: 'status_changed', createdAt: '2026-09-17 05:39:00' },
        { sequence: 3, type: 'status_changed', occurredAt: '2026-09-17T05:39:00' }
      ] }
    })
    await f.selectTask()
    assert.ok(document.querySelector('.cr-detail header').textContent.includes(`Updated ${expected}`))
    const eventTimes = [...document.querySelectorAll('.cr-timeline .cr-small')].map(node => node.textContent)
    assert.deepEqual(eventTimes, [expected, expected, expected])
    assert.doesNotMatch(f.text(), /Time unavailable/)
  } finally {
    if (f) await f.close()
    if (originalTZ === undefined) delete process.env.TZ
    else process.env.TZ = originalTZ
  }
})
