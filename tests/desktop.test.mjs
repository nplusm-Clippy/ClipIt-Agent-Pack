import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import vm from 'node:vm'
import { webcrypto } from 'node:crypto'

const source = await readFile(new URL('../desktop/plugin.js', import.meta.url), 'utf8')

async function fixture(handler = () => ({ items: [], page: {} })) {
  const timers = new Map(), storage = new Map(), disposers = [], contributions = [], calls = []
  let profile = 'default', timerId = 0
  const profileListeners = new Set()
  const host = { state: { profile: { get: () => profile, subscribe(fn) { profileListeners.add(fn); return () => profileListeners.delete(fn) } } }, notify() {}, navigate() {} }
  const context = vm.createContext({ console, URL, TextEncoder, fetch() { throw new Error('Unexpected upload') }, crypto: webcrypto, document: { hidden: false },
    setTimeout(fn, delay) { timers.set(++timerId, { fn, delay }); return timerId }, clearTimeout(id) { timers.delete(id) } })
  const react = { createElement() {}, useEffect() {}, useRef() {}, useState() {}, useSyncExternalStore() {} }
  const sdk = { host, useValue() {}, usePluginI18n() { return value => value }, Button() {}, Input() {}, Textarea() {},
    ROUTES_AREA: 'routes', SIDEBAR_NAV_AREA: 'sidebar.nav', STATUSBAR_AREAS: { right: 'statusbar.right' }, PALETTE_AREA: 'palette', PANES_AREA: 'panes', COMPOSER_AREAS: { attachments: 'composer.attachments' } }
  const modules = Object.fromEntries(Object.entries({ react, '@hermes/plugin-sdk': sdk }).map(([name, exports]) => [name,
    new vm.SyntheticModule(Object.keys(exports), function () { for (const [key, value] of Object.entries(exports)) this.setExport(key, value) }, { context })]))
  const module = new vm.SourceTextModule(source, { context })
  await module.link(name => { assert.ok(modules[name], `disallowed native import ${name}`); return modules[name] })
  await module.evaluate()
  const ctx = {
    async rest(path, options) {
      calls.push({ path, options })
      if (path === '/status') return { accountId: 'owner', credentialId: profile + '-key', connectionId: 'a'.repeat(64), connected: true, compatibility: { contractVersion: '2026-09-16', features: { coordinatedPolling: false } } }
      return handler(path, options)
    },
    storage: { get: (key, fallback) => storage.has(key) ? storage.get(key) : fallback, set: (key, value) => storage.set(key, value) },
    i18n: { register() {} }, os: { notify() {}, openExternal() {} }, onDispose: fn => disposers.push(fn), registerMany: values => contributions.push(...values)
  }
  return { ctx, module, calls, timers, storage, disposers, contributions, profileListeners,
    switchProfile(value) { profile = value; profileListeners.forEach(fn => fn()) } }
}

test('registration contributes expected native areas with no requests until view opens', async () => {
  const f = await fixture()
  f.module.namespace.default.register(f.ctx)
  assert.equal(f.calls.length, 0)
  assert.equal(f.module.namespace.default.defaultEnabled, false)
  assert.ok(f.contributions.some(value => value.area === 'routes' && value.data.path === '/clipit'))
  assert.equal(f.contributions.filter(value => value.area === 'palette').length, 5)
  for (const dispose of f.disposers) dispose()
  assert.equal(f.profileListeners.size, 0)
})

test('100 enable/unload cycles leave no timers, subscriptions or background requests', async () => {
  const f = await fixture()
  for (let i = 0; i < 100; i++) {
    f.module.namespace.default.register(f.ctx)
    for (const dispose of f.disposers.splice(0)) dispose()
  }
  assert.equal(f.timers.size, 0)
  assert.equal(f.profileListeners.size, 0)
  assert.equal(f.calls.length, 0)
})

test('manual polling mode starts no timers', async () => {
  const f = await fixture()
  const controller = f.module.namespace.createController(f.ctx)
  const unmount = controller.mount()
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(f.timers.size, 0)
  assert.ok(f.calls.some(value => value.path === '/operations/overview'))
  unmount(); controller.close()
})

test('mutation receipt is persisted before dispatch and blocks blind second execution', async () => {
  const f = await fixture((path, options) => {
    if (path === '/operations/execute') {
      const saved = [...f.storage.values()][0]
      assert.equal(saved.pending, true)
      assert.equal(saved.idempotencyKey, options.body.body.idempotencyKey)
      assert.equal(options.body.connectionId, 'a'.repeat(64))
      throw new Error('connection lost')
    }
    return { items: [] }
  })
  const c = f.module.namespace.createController(f.ctx)
  await c.refresh()
  await assert.rejects(c.mutate('execute', { request: { functionName: 'newCapability', parameters: {} } }), /connection lost/)
  await assert.rejects(c.mutate('execute', { request: {} }), /pending operation/)
  assert.equal(f.calls.filter(value => value.path === '/operations/execute').length, 1)
  const saved = JSON.stringify([...f.storage.values()])
  assert.ok(!saved.includes('parameters'))
  c.close()
})

test('profile change clears cached runs and ignores stale in-flight read result', async () => {
  let resolveRun
  const f = await fixture(path => path === '/operations/run' ? new Promise(resolve => { resolveRun = resolve }) : { items: [], page: {} })
  const c = f.module.namespace.createController(f.ctx)
  await c.refresh()
  const flight = c.loadRun('old-account-run')
  c.profileChanged()
  resolveRun({ id: 'old-account-run', status: 'running' })
  await assert.rejects(flight, /connection changed/)
  assert.equal(c.snapshot().selected, null)
  assert.equal(c.snapshot().connected, false)
  c.close()
})

test('a persisted URL import resumes after restart and clears on profile change', async () => {
  const f = await fixture(path => {
    if (path === '/operations/import_url') return { operationId: 'import-operation', jobId: 'import-job', status: 'accepted' }
    if (path === '/operations/job') return { id: 'import-job', status: 'completed', result: { videoId: 'imported-video' } }
    return { items: [], page: {} }
  })
  const first = f.module.namespace.createController(f.ctx)
  await first.refresh()
  await first.mutate('import_url', { url: 'https://example.com/source.mp4' })
  first.close()
  const resumed = f.module.namespace.createController(f.ctx)
  await resumed.refresh(); await resumed.checkImport()
  assert.equal(resumed.snapshot().sourceImport.videoId, 'imported-video')
  assert.equal(f.calls.filter(call => call.path === '/operations/import_url').length, 1)
  resumed.profileChanged()
  assert.equal(resumed.snapshot().sourceImport, null)
  resumed.close()
})

test('definitive rejection preserves its key without blocking later mutations', async () => {
  let attempts = 0
  const f = await fixture(path => path === '/operations/execute' ? ++attempts === 1
    ? { ok: false, error: { code: 'RATE_LIMITED', message: 'Wait for quota', status: 429, outcomeUnknown: false } }
    : { status: 'completed', operationId: 'second-operation' } : { items: [] })
  const c = f.module.namespace.createController(f.ctx)
  await c.refresh()
  await assert.rejects(c.mutate('execute', { request: {} }), /Wait for quota/)
  assert.equal(c.snapshot().receipt.pending, false)
  assert.ok(c.snapshot().receipt.idempotencyKey)
  assert.equal(c.snapshot().receipt.status, 'rejected')
  await c.mutate('execute', { request: {} })
  assert.equal(attempts, 2)
  c.close()
})

test('HTTP success with uncertain outcome blocks replay; acknowledged run control can recover', async () => {
  const f = await fixture(path => {
    if (path === '/operations/control') return { status: 'outcome_unknown', operationId: 'control-operation', runId: 'run-1' }
    if (path === '/operations/operation') return { status: 'paused', runId: 'run-1', operationId: 'control-operation' }
    return { items: [] }
  })
  const c = f.module.namespace.createController(f.ctx)
  await c.refresh()
  await assert.rejects(c.mutate('control', { action: 'pause' }, 'run-1'), /outcome is uncertain/)
  assert.equal(c.snapshot().receipt.pending, true)
  await assert.rejects(c.mutate('control', { action: 'pause' }, 'run-1'), /pending operation/)
  await c.recover()
  assert.equal(c.snapshot().receipt.pending, false)
  assert.equal(c.snapshot().receipt.status, 'paused')
  c.close()
})

test('an accepted run opens its inspector inside the existing action', async () => {
  const f = await fixture(path => path === '/operations/run' ? { id: 'new-run', status: 'running' } : { items: [], page: {} })
  const c = f.module.namespace.createController(f.ctx)
  await c.refresh(); await c.perform(() => c.openRun('new-run'))
  assert.equal(c.snapshot().tab, 'Runs')
  assert.equal(c.snapshot().selected.id, 'new-run')
  assert.equal(f.calls.filter(call => call.path === '/operations/run').length, 1)
  c.close()
})

test('async toolkit acknowledgements resolve receipts without treating acceptance as completion', async () => {
  for (const result of [{ jobId: 'job-1' }, { exportJobId: 'export-1' }, { generationId: 'generation-1' }, { status: 'processing' }]) {
    const f = await fixture(path => path === '/operations/execute' ? { status: 'accepted', operationId: 'operation-1', result: { success: true, result } } : { items: [] })
    const c = f.module.namespace.createController(f.ctx)
    await c.refresh(); await c.mutate('execute', { request: {} })
    assert.equal(c.snapshot().receipt.pending, false)
    assert.equal(c.snapshot().receipt.status, 'accepted')
    c.close()
  }
})

test('credential rotation and new mutations clear earlier recovery output', async () => {
  let credential = 'first'
  const f = await fixture(path => path === '/operations/operation'
    ? { status: 'completed', operationId: 'old-operation', result: { privateSummary: 'old account' } }
    : path === '/operations/execute' ? { status: 'completed', operationId: 'new-operation' } : { items: [] })
  const rest = f.ctx.rest
  f.ctx.rest = async (...args) => {
    const result = await rest(...args)
    if (args[0] === '/status') result.credentialId = credential
    return result
  }
  const c = f.module.namespace.createController(f.ctx)
  await c.refresh(); await c.mutate('execute', { request: {} }); await c.recover()
  assert.ok(c.snapshot().recovery)
  await c.mutate('execute', { request: {} })
  assert.equal(c.snapshot().recovery, null)
  await c.recover(); credential = 'second'; await c.refresh()
  assert.equal(c.snapshot().recovery, null)
  assert.equal(c.snapshot().receipt, null)
  c.close()
})

test('same timestamp incremental event cursor is retained when hasMore is false', async () => {
  let eventCalls = 0
  const f = await fixture((path, options) => {
    if (path === '/operations/run') return { id: 'run-1', status: 'running' }
    if (path === '/operations/events') {
      eventCalls++
      if (eventCalls === 2) assert.equal(options.body.query.cursor, 'cursor-1')
      return { items: [{ sequence: String(eventCalls), message: 'event' }], page: { hasMore: false, nextCursor: null, resumeCursor: 'cursor-' + eventCalls } }
    }
    return { items: [], page: {} }
  })
  const c = f.module.namespace.createController(f.ctx)
  await c.refresh(); await c.loadRun('run-1'); await c.loadRun('run-1', true)
  assert.equal(c.snapshot().events.length, 2)
  c.close()
})

test('a newly discovered tool executes without rebuilding the plugin', async () => {
  const f = await fixture((path, options) => {
    if (path === '/operations/catalog') return { items: [{ name: 'futureTool', parameters: { type: 'object' }, available: true }] }
    if (path === '/operations/execute') return { operationId: 'receipt-1', status: 'completed', result: options.body.body.request }
    return { items: [] }
  })
  const c = f.module.namespace.createController(f.ctx)
  await c.tab('Capabilities')
  assert.equal(c.snapshot().capabilities[0].name, 'futureTool')
  const result = await c.mutate('execute', { request: { functionName: 'futureTool', parameters: { preserved: [1, 2, 3] } } })
  assert.equal(result.result.functionName, 'futureTool')
  assert.equal(result.result.parameters.preserved.length, 3)
  c.close()
})

test('multipart resume validates file identity, skips verified parts and stores no signed URLs', async () => {
  const f = await fixture()
  const blob = new Blob(['abcdefghij'])
  const file = { name: 'video.mp4', size: blob.size, lastModified: 1, type: 'video/mp4', slice: (...args) => blob.slice(...args) }
  let receipt = null, putCount = 0, completed = false
  const uploaded = new Set()
  const call = async (operation, args) => {
    if (operation === 'upload_create') return { intentId: 'intent-1', jobId: 'job-1', readyForUpload: true, transport: 'multipart', partCount: 2, partSizeBytes: 5 }
    if (operation === 'upload_status') return { uploadedParts: [...uploaded].map(partNumber => ({ partNumber })) }
    if (operation === 'upload_parts') return { signedPartUrls: [{ partNumber: args.body.partNumbers[0], expectedSizeBytes: 5, url: `https://storage.example.test/${args.body.partNumbers[0]}?X-Amz-Signature=ephemeral` }] }
    if (operation === 'upload_complete') { completed = true; return { status: 'processing' } }
    throw new Error(operation)
  }
  const put = async (url, options) => {
    putCount++
    if (putCount === 2) throw new Error('disconnect')
    uploaded.add(Number(new URL(url).pathname.slice(1)))
    assert.equal(options.body.size, 5)
    assert.equal(options.credentials, 'omit')
    return { ok: true }
  }
  const input = { call, file, save: value => { receipt = value }, signal: new AbortController().signal, put }
  await assert.rejects(f.module.namespace.uploadVideo(input), /disconnect/)
  assert.equal(completed, false)
  assert.ok(receipt.fileHash)
  assert.ok(!JSON.stringify(receipt).includes('X-Amz-Signature'))
  await f.module.namespace.uploadVideo({ ...input, receipt })
  assert.equal(completed, true)
  assert.equal(putCount, 3, 'verified first part was not transferred twice')
  const changed = new Blob(['abcdxxxxxx'])
  await assert.rejects(f.module.namespace.uploadVideo({ ...input, receipt, file: { ...file, slice: (...args) => changed.slice(...args) } }), /content changed/)
})

test('hashing buffers are capped at 8 MiB even when the server uses larger upload parts', async () => {
  const f = await fixture()
  const blob = new Blob([new Uint8Array(17 * 1024 * 1024)])
  let largest = 0
  const wrap = value => ({ size: value.size, slice: (...args) => wrap(value.slice(...args)), arrayBuffer: () => { largest = Math.max(largest, value.size); return value.arrayBuffer() } })
  const file = { name: 'large.mp4', size: blob.size, type: 'video/mp4', lastModified: 1, slice: (...args) => wrap(blob.slice(...args)) }
  await f.module.namespace.uploadVideo({ file, signal: new AbortController().signal, save() {},
    call: async operation => operation === 'upload_create' ? { intentId: 'intent', readyForUpload: false } : { status: 'processing' } })
  assert.ok(largest <= 8 * 1024 * 1024)
})


test('upload checkpoint and dispatch remain bound to their original profile', async () => {
  const f = await fixture()
  const c = f.module.namespace.createController(f.ctx)
  await c.refresh()
  const upload = c.uploadSession()
  upload.save({ version: 1, intentId: 'original-intent' })
  c.profileChanged()
  assert.throws(() => upload.save({ intentId: 'wrong-account' }), /connection changed/)
  assert.throws(() => upload.call('upload_complete', { id: 'original-intent' }), /connection changed/)
  assert.equal(c.snapshot().uploadReceipt, null)
  assert.equal(f.calls.filter(call => call.path === '/operations/upload_complete').length, 0)
  c.close()
})

test('new profile can refresh while an old profile operation finishes', async () => {
  let finish
  const f = await fixture()
  const c = f.module.namespace.createController(f.ctx)
  await c.refresh()
  const prior = c.perform(() => new Promise(resolve => { finish = resolve }))
  c.profileChanged()
  await c.perform(c.refresh)
  assert.equal(c.snapshot().connected, true)
  finish()
  await prior
  assert.equal(c.snapshot().busy, false)
  c.close()
})


test('one snapshot poll updates terminal runs, retains cursor and honors shared Retry-After', async () => {
  let pollCount = 0
  const f = await fixture((path, options) => {
    if (path === '/operations/runs') return { items: [{ id: 'run-1', status: 'running' }], page: {} }
    if (path === '/operations/poll_budget') {
      pollCount++
      assert.equal(options.body.body.runIds[0], 'run-1')
      if (pollCount === 1) return { allowed: true, intervalMs: 5000, overview: { runs: [] }, runs: [{ id: 'run-1', status: 'completed' }] }
      return { ok: false, error: { message: 'Shared poll cadence', status: 429, retryAfter: 45 } }
    }
    return { items: [], page: {} }
  })
  const rest = f.ctx.rest
  f.ctx.rest = async (...args) => {
    const result = await rest(...args)
    if (args[0] === '/status') result.compatibility = { contractVersion: '2026-09-16', features: { coordinatedPolling: true }, limits: { recommendedPollSeconds: 5 } }
    return result
  }
  const c = f.module.namespace.createController(f.ctx)
  const unmount = c.mount()
  await new Promise(resolve => setImmediate(resolve))
  await c.tab('Runs')
  const before = f.calls.length
  let timer = [...f.timers.values()][0]
  f.timers.clear(); await timer.fn()
  assert.equal(c.snapshot().runs[0].status, 'completed')
  assert.equal(f.calls.length - before, 1, 'poll makes no follow-up reads')
  timer = [...f.timers.values()][0]
  f.timers.clear(); await timer.fn()
  assert.equal([...f.timers.values()][0].delay, 45000)
  assert.equal(c.snapshot().error, null)
  unmount(); c.close()
  assert.equal(f.timers.size, 0)
})

test('completed selection keeps shared attention polling active without detailed follow-up reads', async () => {
  const f = await fixture((path, options) => {
    if (path === '/operations/run') return { id: options.body.id, status: 'completed' }
    if (path === '/operations/runs') return { items: [{ id: 'done', status: 'completed' }] }
    if (path === '/operations/poll_budget') return { intervalMs: 5000, overview: { runs: [{ id: 'another', status: 'awaiting_approval' }] }, runs: [] }
    return { items: [] }
  })
  const rest = f.ctx.rest
  f.ctx.rest = async (...args) => { const data = await rest(...args); if (args[0] === '/status') data.compatibility.features.coordinatedPolling = true; return data }
  const c = f.module.namespace.createController(f.ctx), unmount = c.mount()
  await new Promise(resolve => setImmediate(resolve)); await c.select('done')
  const before = f.calls.length, timer = [...f.timers.values()][0]
  assert.ok(timer, 'terminal selection must retain polling')
  f.timers.clear(); await timer.fn()
  assert.equal(f.calls.length - before, 1)
  assert.equal(f.calls.at(-1).options.body.body.runId, undefined)
  assert.equal(c.snapshot().overview.runs[0].id, 'another')
  assert.equal(c.snapshot().selected.id, 'done')
  unmount(); c.close()
})

test('late selected-run poll data cannot replace another selection and repeated events are deduplicated', async () => {
  let resolvePoll
  const f = await fixture((path, options) => {
    if (path === '/operations/run') return { id: options.body.id, status: 'running' }
    if (path === '/operations/events') return { items: [{ sequence: 1, message: options.body.id }], page: { resumeCursor: 'event-1' } }
    if (path === '/operations/poll_budget') return new Promise(resolve => { resolvePoll = resolve })
    return { items: [] }
  })
  const rest = f.ctx.rest
  f.ctx.rest = async (...args) => { const data = await rest(...args); if (args[0] === '/status') data.compatibility.features.coordinatedPolling = true; return data }
  const c = f.module.namespace.createController(f.ctx), unmount = c.mount()
  await new Promise(resolve => setImmediate(resolve)); await c.select('one')
  const timer = [...f.timers.values()][0]; f.timers.clear(); const polling = timer.fn()
  await c.select('two')
  resolvePoll({ overview: { runs: [] }, runs: [], run: { id: 'one', status: 'completed' }, events: { items: [{ sequence: 2, message: 'wrong selection' }] } })
  await polling
  assert.equal(c.snapshot().selected.id, 'two'); assert.equal(c.snapshot().events[0].message, 'two')
  await c.loadRun('two', true)
  assert.equal(c.snapshot().events.length, 1)
  unmount(); c.close()
})

test('workflow filters survive refresh and cursor paging; later filters win over old responses', async () => {
  let resolveFirst, queries = []
  const f = await fixture((path, options) => {
    if (path === '/operations/runs') {
      const query = options.body.query; queries.push(query)
      if (query.search === 'slow') return new Promise(resolve => { resolveFirst = resolve })
      return { items: [{ id: query.cursor ? 'next' : 'first' }], page: { nextCursor: 'cursor-first' } }
    }
    return { items: [] }
  })
  const c = f.module.namespace.createController(f.ctx); await c.refresh()
  const old = c.loadRuns({ search: 'slow' }); await c.loadRuns({ search: 'launch', status: 'attention' })
  resolveFirst({ items: [{ id: 'obsolete' }], page: {} }); await old
  await c.loadRuns({ more: true })
  assert.equal(queries.at(-1).search, 'launch'); assert.equal(queries.at(-1).status, 'attention'); assert.equal(queries.at(-1).cursor, 'cursor-first')
  assert.equal(c.snapshot().runs.length, 2)
  await c.tab('Runs'); assert.equal(queries.at(-1).search, 'launch'); assert.equal(queries.at(-1).cursor, undefined)
  c.close()
})

test('fresh approval rejects changed digest and invalid expiry before any mutation', async () => {
  const approval = { approvalId: 'approval', actionDigest: 'new', expiresAt: '2099-01-01T00:00:00Z' }
  const f = await fixture(path => path === '/operations/run' ? { id: 'run', status: 'awaiting_approval', currentApproval: approval } : { items: [] })
  const c = f.module.namespace.createController(f.ctx); await c.refresh()
  await assert.rejects(c.respondToApproval({ id: 'run' }, { ...approval, actionDigest: 'old' }, 'approved'), /changed or expired/)
  approval.expiresAt = 'invalid'
  await assert.rejects(c.respondToApproval({ id: 'run' }, approval, 'approved'), /changed or expired/)
  assert.equal(f.calls.filter(call => call.path === '/operations/approval').length, 0)
  c.close()
})

test('pause is requested until observed confirmation and definitive rejection releases pending indicator', async () => {
  let status = 'running', reject = false
  const f = await fixture(path => {
    if (path === '/operations/run') return { id: 'run', status, allowedControls: ['pause'] }
    if (path === '/operations/control') return reject ? { ok: false, error: { status: 409, code: 'STALE', message: 'Changed' } } : { runId: 'run', status: 'running' }
    return { items: [] }
  })
  const c = f.module.namespace.createController(f.ctx); await c.refresh()
  await c.control({ id: 'run', status: 'running' }, 'pause')
  assert.equal(c.snapshot().controlRequests.run, 'pause'); assert.equal(c.snapshot().selected.status, 'running')
  status = 'paused'; await c.loadRun('run'); assert.equal(c.snapshot().controlRequests.run, undefined)
  status = 'running'; reject = true
  await assert.rejects(c.control({ id: 'run', status }, 'pause'), /Changed/)
  assert.equal(c.snapshot().controlRequests.run, undefined)
  c.close()
})

test('read navigation stays usable during a serialized write and profile-scoped view preference survives', async () => {
  let finish
  const f = await fixture(path => path === '/operations/run' ? { id: 'selected', status: 'completed' } : { items: [] })
  const c = f.module.namespace.createController(f.ctx); await c.refresh()
  const writing = c.perform(() => new Promise(resolve => { finish = resolve }))
  await c.select('selected'); assert.equal(c.snapshot().selected.id, 'selected'); assert.equal(c.snapshot().busy, true)
  await c.setMode('classic'); assert.equal(f.storage.get('control-room-mode:default'), 'classic')
  f.switchProfile('different'); c.profileChanged(); assert.equal(c.snapshot().uiMode, 'modern')
  f.switchProfile('default'); c.profileChanged(); assert.equal(c.snapshot().uiMode, 'classic')
  finish(); await writing; c.close()
})
