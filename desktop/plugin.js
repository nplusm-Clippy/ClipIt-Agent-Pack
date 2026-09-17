import { createElement as h, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { host, useValue, usePluginI18n, Button, Input, Textarea, ROUTES_AREA, SIDEBAR_NAV_AREA,
  STATUSBAR_AREAS, PALETTE_AREA, PANES_AREA, COMPOSER_AREAS } from '@hermes/plugin-sdk'

export const VERSION = '3.0.0'
export const CONTRACT_VERSION = '2026-09-16'
const TERMINAL = new Set(['completed', 'failed', 'cancelled'])
const operationResolved = value => {
  if (value.status === 'outcome_unknown') return false
  const output = value.result?.result
  return ['completed', 'failed', 'cancelled', 'blocked', 'awaiting_approval'].includes(value.status) ||
    !!(value.runId || value.jobId || value.result?.runId || value.result?.jobId || output?.jobId || output?.exportJobId || output?.generationId) ||
    (value.result?.success === true && ['queued', 'running', 'processing', 'accepted'].includes(output?.status || value.result?.status))
}
const TABS = ['Overview', 'Runs', 'Library', 'Capabilities', 'Settings']
const ENGLISH = { overview: 'Overview', runs: 'Runs', library: 'Library', capabilities: 'Capabilities', settings: 'Settings', refresh: 'Refresh', workspace: 'Your workspace', activity: 'Recent activity', source: 'Start with your source', approvals: 'Approvals', credits: 'Available credits', recipes: 'Outcome recipes', doctor: 'Run Doctor', back: 'Back to runs', steps: 'Steps', events: 'Events', artifacts: 'Artifacts', errors: 'Errors' }
const COPY_KEYS = Object.fromEntries(Object.entries(ENGLISH).map(([key, value]) => [value, key]))
const LOCALES = { en: ENGLISH, es: { overview: 'Resumen', runs: 'Ejecuciones', library: 'Biblioteca', capabilities: 'Capacidades', settings: 'Configuración', refresh: 'Actualizar', workspace: 'Tu espacio de trabajo', activity: 'Actividad reciente', source: 'Empieza con tu fuente', approvals: 'Aprobaciones', credits: 'Créditos disponibles', recipes: 'Recetas de resultados', doctor: 'Ejecutar diagnóstico', back: 'Volver a ejecuciones', steps: 'Pasos', events: 'Eventos', artifacts: 'Resultados', errors: 'Errores' } }
function LocalizedText({ value }) {
  const t = usePluginI18n('clipit')
  return COPY_KEYS[value] ? t(COPY_KEYS[value]) : value
}
const localized = value => h(LocalizedText, { value })
const text = value => value == null ? '—' : typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)
const items = value => value?.items || value?.tools || value?.capabilities || value?.videos || []
const code = value => h('pre', { style: { whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', fontSize: 12, maxHeight: 300, overflow: 'auto', padding: 12, border: '1px solid var(--ui-stroke-secondary)', borderRadius: 8 } }, text(value))
const section = (title, ...children) => h('section', { style: { marginBlock: 18 } }, h('h2', { style: { fontSize: 16, fontWeight: 600, marginBottom: 10 } }, localized(title)), ...children)
const button = (label, onClick, props = {}) => h(Button, { onClick, type: 'button', ...props }, localized(label))
const field = (label, element) => h('label', { style: { display: 'grid', gap: 6, marginBlock: 10 } }, h('span', null, localized(label)), element)

export function createController(ctx) {
  let state = { status: null, tab: 'Overview', runs: [], library: [], capabilities: [], recipes: [], overview: null,
    selected: null, events: [], artifacts: [], error: null, busy: false, receipt: null, uploadReceipt: null, sourceImport: null, connected: false }
  let closed = false, generation = 0, views = 0, timer = null, activeTask = null
  let pollDelay = 5000, selectionRequest = 0
  let scope = '', nextCursor = null, eventCursor = null, libraryCursor = null, refreshFlight = null
  const listeners = new Set(), seen = new Map()
  const update = change => {
    if (closed) return
    state = { ...state, ...change }
    listeners.forEach(fn => fn())
  }
  const call = async (operation, arguments_ = {}) => {
    if (closed) throw new Error('ClipIt is disabled.')
    const epoch = generation
    const result = await ctx.rest(`/operations/${operation}`, { method: 'POST', body: { ...arguments_, connectionId: state.status?.connectionId }, timeoutMs: 65000 })
    if (closed || epoch !== generation) throw new Error('The ClipIt connection changed. Refresh before continuing.')
    if (result?.ok === false) throw Object.assign(new Error(result.error?.message || 'ClipIt request failed.'), { details: result.error })
    return result
  }
  const persistReceipt = receipt => {
    if (!scope) return
    ctx.storage.set(`receipt:${scope}`, receipt ? { version: 1, ...receipt } : null)
    update({ receipt })
  }
  const notify = run => {
    const previous = seen.get(run.id)
    seen.set(run.id, run.status)
    if (seen.size > 200) seen.delete(seen.keys().next().value)
    if (!previous || previous === run.status || !['completed', 'failed', 'awaiting_approval'].includes(run.status)) return
    const message = run.status === 'awaiting_approval' ? 'A ClipIt run needs your approval.' : `ClipIt run ${run.status}.`
    host.notify({ kind: run.status === 'failed' ? 'error' : 'info', message, title: 'ClipIt' })
    void Promise.resolve(ctx.os.notify({ title: 'ClipIt', body: message, activate: '/clipit' })).catch(() => {})
  }
  const loadRun = async (id, append = false) => {
    const request = ++selectionRequest
    const epoch = generation
    const result = await call('run', { id })
    if (epoch !== generation || closed || request !== selectionRequest) return
    const run = result.run || result
    update({ selected: run })
    notify(run)
    const events = await call('events', { id, query: { limit: 100, ...(append && eventCursor ? { cursor: eventCursor } : {}) } })
    if (epoch !== generation || closed || state.selected?.id !== id || request !== selectionRequest) return
    eventCursor = events.page?.resumeCursor || events.page?.nextCursor || eventCursor
    update({ events: append ? [...state.events, ...items(events)].slice(-1000) : items(events) })
    const artifacts = await call('artifacts', { id, query: { limit: 100 } })
    if (epoch === generation && !closed && state.selected?.id === id && request === selectionRequest) update({ artifacts: items(artifacts) })
  }
  const loadRuns = async ({ more = false, status, search } = {}) => {
    const epoch = generation
    const data = await call('runs', { query: { limit: 50, ...(more && nextCursor ? { cursor: nextCursor } : {}), ...(status ? { status } : {}), ...(search ? { search } : {}) } })
    if (epoch !== generation || closed) return
    nextCursor = data.page?.nextCursor
    items(data).forEach(notify)
    update({ runs: more ? [...state.runs, ...items(data)].slice(-500) : items(data), runsHasMore: !!nextCursor })
  }
  const loadLibrary = async (more = false, search = '') => {
    const epoch = generation
    const data = await call('library', { query: { limit: 50, ...(more && libraryCursor ? { cursor: libraryCursor } : {}), ...(search ? { search } : {}) } })
    if (epoch !== generation || closed) return
    libraryCursor = data.page?.nextCursor
    update({ library: more ? [...state.library, ...items(data)].slice(-500) : items(data), libraryHasMore: !!libraryCursor })
  }
  const refresh = async () => {
    if (refreshFlight) return refreshFlight
    let epoch = generation
    const flight = (async () => {
      const connection = await ctx.rest('/status', { timeoutMs: 45000 })
      if (epoch !== generation || closed) return
      if (connection?.ok === false) throw new Error(connection.error?.message || 'Connect ClipIt in the gateway environment.')
      const nextScope = `${host.state.profile.get()}:${connection.connectionId}:${connection.accountId}:${connection.credentialId}`
      if (scope && scope !== nextScope) {
        epoch = ++generation
        seen.clear(); nextCursor = null; libraryCursor = null; eventCursor = null
        update({ runs: [], selected: null, library: [], events: [], artifacts: [], capabilities: [], recipes: [], recipe: null, overview: null, sourceImport: null, recovery: null })
      }
      scope = nextScope
      const rawReceipt = ctx.storage.get(`receipt:${scope}`, null)
      const saved = rawReceipt && rawReceipt.version === 1 && typeof rawReceipt.pending === 'boolean' && /^[a-zA-Z0-9_.:-]{8,128}$/.test(rawReceipt.idempotencyKey || '') ? rawReceipt : rawReceipt ? { version: 1, pending: true, corrupt: true } : null
      const rawUpload = ctx.storage.get(`upload:${scope}`, null)
      const upload = rawUpload && rawUpload.version === 1 && /^[a-zA-Z0-9_.:-]{8,128}$/.test(rawUpload.idempotencyKey || '') && typeof rawUpload.file?.name === 'string' && Number.isSafeInteger(rawUpload.file?.size) && rawUpload.partHashes && Object.keys(rawUpload.partHashes).length <= 10000 ? rawUpload : null
      if (rawUpload && !upload) throw new Error('Saved upload metadata is invalid. Inspect your uploads in ClipIt before resetting this plugin’s local state.')
      update({ status: connection, connected: true, error: null, receipt: saved?.version === 1 ? saved : null, uploadReceipt: upload?.version === 1 ? upload : null })
      if (connection.compatibility?.contractVersion !== CONTRACT_VERSION) return
      if (state.tab === 'Runs') await loadRuns()
      else if (state.tab === 'Library') await loadLibrary()
      else if (state.tab === 'Capabilities') {
        const data = await call('catalog')
        if (epoch === generation && !closed) update({ capabilities: items(data) })
      } else if (state.tab === 'Overview') {
        const data = await call('overview')
        const recipes = await call('recipes')
        if (epoch === generation && !closed) update({ overview: data, recipes: items(recipes) })
      }
    })().finally(() => { if (refreshFlight === flight) refreshFlight = null })
    refreshFlight = flight
    return flight
  }
  const perform = async task => {
    if (activeTask) return
    const token = {}
    activeTask = token
    update({ busy: true, error: null })
    try { return await task() }
    catch (error) { if (activeTask === token) update({ error: error.message || 'ClipIt request failed.' }); return null }
    finally { if (activeTask === token) { activeTask = null; update({ busy: false }) } }
  }
  const mutate = async (operation, body, id) => {
    const epoch = generation
    if (state.receipt?.pending) throw new Error('Resolve the pending operation receipt before starting another mutation.')
    const key = crypto.randomUUID()
    const receipt = { operation, id: id || null, idempotencyKey: key, pending: true }
    update({ recovery: null })
    persistReceipt(receipt)
    let result
    try { result = await call(operation, { ...(id ? { id } : {}), body: { ...body, idempotencyKey: key } }) }
    catch (error) {
      const details = error.details
      if (!closed && epoch === generation && details?.status >= 400 && details.status < 500 && details.status !== 408 && !details.outcomeUnknown) {
        persistReceipt({ ...receipt, pending: false, status: 'rejected', rejectionCode: details.code || 'REQUEST_REJECTED' })
      }
      throw error
    }
    if (closed || epoch !== generation) return null
    const resolved = operationResolved(result)
    persistReceipt({ ...receipt, pending: !resolved, status: result.status, operationId: result.operationId || null, runId: result.runId || result.jobId || null })
    if (!resolved) throw new Error('The operation outcome is uncertain. Look up the original receipt before starting another action.')
    return result
  }
  const recover = async () => {
    const receipt = state.receipt
    if (!receipt) return
    const epoch = generation
    const data = await call('operation', { id: receipt.idempotencyKey })
    if (closed || epoch !== generation) return
    const value = data.operation || data
    persistReceipt({ ...receipt, pending: !operationResolved(value), status: value.status, operationId: value.operationId || value.id || null, runId: value.runId || value.jobId || value.result?.runId || value.result?.jobId || null })
    update({ recovery: data })
    return data
  }
  const stopPolling = () => { if (timer !== null) clearTimeout(timer); timer = null }
  const schedule = () => {
    stopPolling()
    if (closed || views === 0 || !state.status?.compatibility?.features?.coordinatedPolling || state.status?.compatibility?.pollingMode === 'manual') return
    if (state.selected && TERMINAL.has(state.selected.status)) return
    const delay = Math.max(pollDelay, document.hidden ? 60000 : state.status.compatibility.limits?.recommendedPollSeconds * 1000 || 5000)
    timer = setTimeout(async () => {
      timer = null
      if (activeTask || refreshFlight) { schedule(); return }
      const epoch = generation, selectedId = state.selected?.id
      try {
        const snapshot = await call('poll_budget', { body: { ...(selectedId ? { runId: selectedId } : { runIds: state.runs.slice(0, 50).map(run => run.id) }), ...(selectedId && eventCursor ? { cursor: eventCursor } : {}) } })
        if (epoch !== generation || closed || views === 0) return
        pollDelay = Math.max(5000, snapshot.intervalMs || snapshot.retryAfterSeconds * 1000 || 5000)
        update({ overview: snapshot.overview, error: null })
        ;[...(snapshot.overview?.runs || []), ...(snapshot.runs || [])].forEach(notify)
        if (state.tab === 'Runs' && !state.selected) {
          const changes = new Map((snapshot.runs || []).map(run => [run.id, run]))
          update({ runs: state.runs.map(run => changes.has(run.id) ? { ...run, ...changes.get(run.id) } : run) })
        }
        if (snapshot.run && state.selected?.id === snapshot.run.id) {
          const run = { ...state.selected, ...snapshot.run }
          if (snapshot.run.status !== state.selected.status) run.currentApproval = null
          update({ selected: run })
          notify(run)
          if (snapshot.events) {
            eventCursor = snapshot.events.page?.resumeCursor || eventCursor
            update({ events: [...state.events, ...items(snapshot.events)].slice(-1000) })
          }
        }
      } catch (error) {
        if (epoch !== generation || closed) return
        if (error.details?.code === 'CURSOR_EXPIRED') { eventCursor = null; update({ events: [] }) }
        pollDelay = Math.min(300000, Math.max(5000, error.details?.retryAfter * 1000 || pollDelay * 2))
        if (error.details?.status !== 429) update({ error: error.message })
      }
      schedule()
    }, delay)
  }
  return {
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn) }, snapshot: () => state,
    call, perform, mutate, recover, refresh, loadRuns, loadLibrary, loadRun,
    showRecipe(recipe) { update({ recipe }) },
    async checkImport() {
      const receipt = state.receipt
      if (receipt?.operation !== 'import_url' || !receipt.runId) throw new Error('Look up the original import receipt first.')
      const job = await call('job', { id: receipt.runId })
      update({ sourceImport: { jobId: receipt.runId, status: job.status, progress: job.progress, videoId: job.videoId || job.result?.videoId || null } })
    },
    clearReceipt() { persistReceipt(null); update({ recovery: null }) },
    saveUpload(receipt) { if (scope) { ctx.storage.set(`upload:${scope}`, receipt); update({ uploadReceipt: receipt }) } },
    uploadSession() {
      const epoch = generation, target = scope
      const check = () => { if (closed || epoch !== generation || scope !== target || !target) throw new Error('The ClipIt connection changed. Resume in the original profile.') }
      return { call: (...args) => { check(); return call(...args) }, save(receipt) { check(); ctx.storage.set(`upload:${target}`, receipt); update({ uploadReceipt: receipt }) } }
    },
    mount() { views += 1; perform(refresh).then(schedule); return () => { views -= 1; if (views === 0) stopPolling() } },
    async tab(tab) { update({ tab, error: null }); await perform(refresh); schedule() },
    async select(id) { eventCursor = null; await perform(() => loadRun(id)); schedule() },
    async openRun(id) { update({ tab: 'Runs' }); eventCursor = null; await loadRun(id); schedule() },
    clearSelected() { update({ selected: null, events: [], artifacts: [] }); eventCursor = null; schedule() },
    profileChanged() {
      generation += 1; scope = ''; seen.clear(); stopPolling(); refreshFlight = null; activeTask = null; pollDelay = 5000
      state = { status: null, tab: 'Overview', runs: [], library: [], capabilities: [], selected: null,
        overview: null, recipes: [], recipe: null, events: [], artifacts: [], receipt: null, uploadReceipt: null, sourceImport: null, connected: false, busy: false, error: null }
      listeners.forEach(fn => fn())
      if (views) perform(refresh).then(schedule)
    },
    close() { closed = true; generation += 1; stopPolling(); listeners.clear(); seen.clear() }
  }
}

export async function uploadVideo({ call, file, receipt, save, signal, onProgress = () => {}, put = fetch }) {
  const identity = { name: file.name, size: file.size, lastModified: file.lastModified, type: file.type || 'video/mp4' }
  if (receipt && JSON.stringify(receipt.file) !== JSON.stringify(identity)) throw new Error('Select the same original file to resume, or abort the previous upload first.')
  let checkpoint = receipt || { version: 1, file: identity, idempotencyKey: crypto.randomUUID(), intentId: null, partHashes: {} }
  const store = change => { checkpoint = { ...checkpoint, ...change }; save(checkpoint) }
  const check = () => { if (signal.aborted) throw new Error('Upload paused. Re-select this file to resume.') }
  const fingerprint = async blob => {
    const hashes = []
    for (let offset = 0; offset < blob.size; offset += 8 * 1024 * 1024) {
      check()
      const hash = await crypto.subtle.digest('SHA-256', await blob.slice(offset, offset + 8 * 1024 * 1024).arrayBuffer())
      hashes.push([...new Uint8Array(hash)].map(value => value.toString(16).padStart(2, '0')).join(''))
    }
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(hashes.join(':')))
    return [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, '0')).join('')
  }
  const transfer = async (url, blob, headers = {}) => {
    check()
    const target = new URL(url)
    if (target.protocol !== 'https:' || target.username || target.password) throw new Error('Invalid storage destination.')
    const allowed = Object.fromEntries(Object.entries(headers).filter(([name]) => name.toLowerCase() !== 'content-length'))
    const response = await put(url, { method: 'PUT', body: blob, headers: allowed, credentials: 'omit', redirect: 'error', signal })
    if (!response.ok) throw new Error('Upload interrupted. Resume with the same file and upload intent.')
  }
  store({ status: 'preparing' })
  check()
  const fileHash = await fingerprint(file)
  if (checkpoint.fileHash && checkpoint.fileHash !== fileHash) throw new Error('The selected file content changed. Abort this intent before starting a new upload.')
  store({ fileHash })
  const intent = await call('upload_create', { body: { filename: file.name, size: file.size, contentType: identity.type, idempotencyKey: checkpoint.idempotencyKey } })
  store({ intentId: intent.intentId, jobId: intent.jobId, status: 'uploading' })
  if (!intent.readyForUpload) {
    const existing = await call('upload_status', { id: intent.intentId })
    store({ status: existing.status, videoId: existing.videoId || null })
    return existing
  }
  const status = await call('upload_status', { id: intent.intentId })
  if (intent.transport === 'single') {
    await transfer(intent.uploadUrl, file, intent.requiredHeaders)
    onProgress(100)
  } else {
    if (!Number.isInteger(intent.partCount) || intent.partCount < 1 || intent.partCount > 10000 || !Number.isSafeInteger(intent.partSizeBytes) || intent.partSizeBytes < 1 || Math.ceil(file.size / intent.partSizeBytes) !== intent.partCount) throw new Error('Invalid multipart upload geometry.')
    const uploaded = new Set((status.uploadedParts || []).map(part => part.partNumber))
    for (let part = 1; part <= intent.partCount; part += 1) {
      check()
      const start = (part - 1) * intent.partSizeBytes
      const chunk = file.slice(start, Math.min(file.size, start + intent.partSizeBytes))
      const hash = await fingerprint(chunk)
      const priorHash = checkpoint.partHashes[part]
      if (priorHash && priorHash !== hash) throw new Error('The selected file differs from the original upload. Abort this intent and start a new upload.')
      if (uploaded.has(part) && !priorHash) throw new Error('Cannot verify a part uploaded by another client. Continue from its original verified receipt.')
      if (!uploaded.has(part)) {
        const signed = (await call('upload_parts', { id: intent.intentId, body: { partNumbers: [part] } })).signedPartUrls?.[0]
        if (!signed || signed.partNumber !== part || signed.expectedSizeBytes !== chunk.size) throw new Error('Storage returned an unexpected upload part.')
        store({ partHashes: { ...checkpoint.partHashes, [part]: hash } })
        await transfer(signed.url, chunk)
      }
      onProgress(Math.round(part / intent.partCount * 100))
    }
  }
  check()
  store({ status: 'completing' })
  const completed = await call('upload_complete', { id: intent.intentId, body: {} })
  store({ status: completed.status || 'processing', videoId: completed.videoId || null })
  return completed
}

function Receipt({ controller, state }) {
  if (!state.receipt) return null
  return section(state.receipt.pending ? 'Operation outcome needs checking' : state.receipt.status === 'rejected' ? 'Request rejected' : 'Latest operation receipt',
    h('p', null, state.receipt.pending ? 'Keep this operation key. A lost connection does not mean the action failed.' : state.receipt.status === 'rejected' ? 'ClipIt rejected this request. Resolve the reported issue before trying again.' : 'The request has a durable receipt; inspect the run before claiming completion.'),
    code(state.receipt), state.receipt.corrupt ? h('p', { role: 'alert' }, 'The saved recovery record is unreadable. Inspect your runs and recent activity in ClipIt before clearing it.') : button('Look up outcome', () => controller.perform(controller.recover), { disabled: state.busy }),
    state.receipt.corrupt ? button('Clear unreadable recovery record', () => { if (window.confirm('Have you checked ClipIt for the original operation? Clearing this record cannot cancel or undo it.')) controller.clearReceipt() }) : null,
    state.receipt.operation === 'import_url' && state.receipt.runId ? button('Check imported video', () => controller.perform(controller.checkImport), { disabled: state.busy }) : null,
    state.sourceImport ? code(state.sourceImport) : null,
    state.recovery ? code(state.recovery) : null)
}

function Intake({ controller, state }) {
  const [goal, setGoal] = useState(''), [source, setSource] = useState(''), [kind, setKind] = useState('video')
  const [file, setFile] = useState(null), [upload, setUpload] = useState(null), [progress, setProgress] = useState(0)
  const uploadAbort = useRef(null)
  useEffect(() => () => uploadAbort.current?.abort(), [])
  useEffect(() => {
    if (state.sourceImport?.videoId) { setKind('video'); setSource(state.sourceImport.videoId) }
  }, [state.sourceImport?.videoId])
  const start = () => controller.perform(async () => {
    let videoId = kind === 'video' ? source.trim() : undefined
    if (kind === 'url' && source.trim()) {
      const parsed = new URL(source)
      if (!['https:', 'http:'].includes(parsed.protocol)) throw new Error('Enter a public video URL.')
      const result = await controller.mutate('import_url', { url: source.trim() })
      setUpload(result)
      return
    }
    if (!goal.trim()) throw new Error('Describe the outcome you want.')
    const result = await controller.mutate('orchestrate', { request: { userMessage: goal.trim(), ...(videoId ? { videoId } : {}), autoConfirmCostlyTools: false } })
    if (result?.runId) await controller.openRun(result.runId)
  })
  const uploadFile = () => controller.perform(async () => {
    if (!file) throw new Error('Select a local video file.')
    uploadAbort.current = new AbortController()
    const session = controller.uploadSession()
    const completed = await uploadVideo({ call: session.call, file, receipt: state.uploadReceipt, signal: uploadAbort.current.signal,
      save: value => { session.save(value); setUpload(value) }, onProgress: setProgress })
    if (completed.videoId) { setKind('video'); setSource(completed.videoId) }
  })
  return section('Start with your source',
    field('Source', h('select', { value: kind, onChange: e => setKind(e.target.value), style: { color: 'inherit', background: 'var(--ui-bg-base)', padding: 8 } },
      h('option', { value: 'video' }, 'Existing ClipIt video'), h('option', { value: 'url' }, 'Import a URL'), h('option', { value: 'file' }, 'Upload a local file'))),
    kind === 'file' ? h('div', null,
      field('Video on this device', h('input', { type: 'file', accept: 'video/*', onChange: e => { setFile(e.target.files?.[0] || null); setProgress(0) } })),
      h('p', null, 'The selected file uploads directly from this device to ClipIt storage, including when Hermes uses a remote gateway.'),
      button(state.uploadReceipt ? 'Resume upload' : 'Upload video', uploadFile, { disabled: state.busy || !file }),
      state.busy && upload?.intentId ? button('Pause transfer', () => uploadAbort.current?.abort()) : null,
      h('progress', { value: progress, max: 100, 'aria-label': 'Video upload progress' })) :
      field(kind === 'url' ? 'Video URL' : 'Video ID (optional)', h(Input, { value: source, onChange: e => setSource(e.target.value) })),
    field('What should Clippy create?', h(Textarea, { value: goal, maxLength: 4000, onChange: e => setGoal(e.target.value), placeholder: 'Find the strongest moments, prepare a vertical edit, and stop for review.' })),
    button(kind === 'url' ? 'Import source' : 'Start Clippy run', start, { disabled: state.busy || kind === 'file' }),
    (upload || state.uploadReceipt) ? h('div', null, code(upload || state.uploadReceipt), (upload || state.uploadReceipt).intentId ? button('Check upload', () => controller.perform(async () => {
      const result = await controller.call('upload_status', { id: (upload || state.uploadReceipt).intentId })
      setUpload(result)
      if (result.videoId) { setKind('video'); setSource(result.videoId) }
    }), { disabled: state.busy }) : button('Check source import', () => controller.perform(async () => {
      const receipt = upload?.result || upload
      const result = await controller.call('job', { id: receipt.jobId || upload?.jobId })
      setUpload({ ...upload, progress: result.progress, status: result.status })
      const videoId = result.videoId || result.result?.videoId
      if (videoId) { setKind('video'); setSource(videoId) }
    }), { disabled: state.busy }),
    state.uploadReceipt?.intentId && !['processing', 'completed'].includes((upload || state.uploadReceipt).status) ? button('Abort upload', () => controller.perform(async () => {
      if (!window.confirm('Abort this upload intent?')) return
      await controller.call('upload_abort', { id: state.uploadReceipt.intentId })
      controller.saveUpload(null); setUpload(null); setProgress(0)
    }), { disabled: state.busy }) : null,
    state.uploadReceipt && ['processing', 'completed'].includes((upload || state.uploadReceipt).status) ? button('Start another upload', () => {
      controller.saveUpload(null); setUpload(null); setFile(null); setProgress(0)
    }, { disabled: state.busy }) : null) : null)
}

function Approval({ controller, state, run }) {
  const approval = run.currentApproval
  const [confirmed, setConfirmed] = useState(false)
  useEffect(() => setConfirmed(false), [approval?.approvalId, approval?.actionDigest])
  if (!approval) return null
  const expired = Date.parse(approval.expiresAt) <= Date.now()
  const submit = decision => controller.perform(async () => {
    const result = await controller.mutate('approval', { approvalId: approval.approvalId || approval.id, actionDigest: approval.actionDigest, decision }, run.id)
    if (result) await controller.loadRun(result.runId || run.id)
  })
  return section('Approval required', code(approval),
    field('I approve these exact actions and estimated cost.', h('input', { type: 'checkbox', checked: confirmed, onChange: e => setConfirmed(e.target.checked), disabled: expired || state.busy })),
    button('Approve actions', () => submit('approved'), { disabled: expired || !confirmed || state.busy }),
    button('Decline actions', () => submit('cancelled'), { disabled: expired || state.busy }),
    expired ? h('p', { role: 'status' }, 'This approval expired. Refresh the run.') : null)
}

function ArtifactList({ controller, state, artifacts }) {
  const [download, setDownload] = useState(null), [delivery, setDelivery] = useState(null), [preview, setPreview] = useState(false)
  const [clipId, setClipId] = useState(''), [exportId, setExportId] = useState('')
  const choose = id => { setClipId(id); setExportId(''); setDownload(null); setDelivery(null); setPreview(false) }
  const inspect = () => controller.perform(async () => {
    setDownload(null); setPreview(false)
    const value = await controller.call('delivery_state', { id: clipId, ...(exportId ? { query: { exportId } } : {}) })
    setDelivery(value)
    if (value.selectedExport?.exportId) setExportId(value.selectedExport.exportId)
  })
  return h('div', null,
    artifacts.length ? h('ul', { style: { listStyle: 'none', padding: 0 } }, artifacts.map(item => h('li', { key: item.id, style: { padding: 12, borderBottom: '1px solid var(--ui-stroke-secondary)' } },
      h('strong', null, item.label || item.kind), h('span', { style: { marginLeft: 12 } }, item.status),
      h('div', { style: { overflowWrap: 'anywhere' } }, item.resourceId || item.resourceRef?.id), h('small', null, `Run ${item.runId || state.selected?.id || '—'}`),
      item.kind === 'clip' ? button('Inspect this clip', () => choose(item.resourceId), { disabled: state.busy }) : null,
      ['clip', 'video', 'project'].includes(item.kind) ? button('Open in editor', () => ctxOpen(controller, state.status, `/editor?${item.kind}=${encodeURIComponent(item.resourceId)}`)) : null,
      item.qa ? code(item.qa) : null))) : h('p', null, 'No associated artifacts yet.'),
    h('p', null, 'An associated artifact is not proof that QA passed or that an export matches the current edit.'),
    field('Clip ID for exact delivery', h(Input, { value: clipId, onChange: e => choose(e.target.value) })),
    button('Inspect delivery readiness', inspect, { disabled: state.busy || !clipId }),
    delivery ? section('Delivery and publish preparation',
      h('p', null, delivery.guidance || 'Review the exact artifact and its delivery blockers before publishing.'),
      delivery.deliveryBlockers?.length ? code(delivery.deliveryBlockers) : null,
      code({ editorStateStatus: delivery.editorStateStatus, selectedExport: delivery.selectedExport, readyToPublish: delivery.readyToPublish }),
      (delivery.exports || []).length ? field('Export to review', h('select', { value: exportId, onChange: e => { setExportId(e.target.value); setDownload(null); setPreview(false) } },
        h('option', { value: '' }, 'Choose an exact export'), ...delivery.exports.map(value => h('option', { key: value.exportId, value: value.exportId }, value.exportId)))) : null) : null,
    field('Current export ID', h(Input, { value: exportId, onChange: e => { setExportId(e.target.value); setDownload(null); setPreview(false) } })),
    button('Check and prepare download', () => controller.perform(async () => {
      setDownload(null); setPreview(false)
      const result = await controller.call('download', { id: clipId, query: { exportId } })
      const url = result.downloadUrl || result.url
      const parsed = new URL(url)
      if (parsed.protocol !== 'https:' || parsed.username || parsed.password) throw new Error('ClipIt returned an invalid download URL.')
      setDownload({ url, expiresAt: result.expiresAt, exportId: result.exportId })
    }), { disabled: state.busy || !clipId || !exportId }),
    download ? h('div', null,
      h('p', null, `Exact export ${download.exportId || exportId}. Refresh this link after it expires or the edit changes.`),
      button(preview ? 'Close preview' : 'Preview exact export', () => setPreview(!preview)),
      preview ? h('video', { src: download.url, controls: true, preload: 'metadata', style: { width: '100%', maxHeight: 420, display: 'block', marginBlock: 12 }, 'aria-label': 'Exact export preview' }) : null,
      h('a', { href: download.url, target: '_blank', rel: 'noopener noreferrer', referrerPolicy: 'no-referrer', style: { display: 'block', marginTop: 12 } }, 'Download this exact export')) : null)
}

function Runs({ controller, state }) {
  const [search, setSearch] = useState(''), [status, setStatus] = useState('')
  const run = state.selected
  if (run) return h('div', null,
    button('Back to runs', controller.clearSelected), section(run.name || run.id,
      h('p', null, `${run.status} · ${run.progress || 0}%`), h('progress', { max: 100, value: run.progress || 0, 'aria-label': 'Run progress' }),
      h('p', null, run.goal || ''), code({ costs: run.costs, qa: run.qa, lineage: run.lineage }),
      button('Refresh run', () => controller.perform(() => controller.loadRun(run.id, true)), { disabled: state.busy }),
      ...(run.allowedControls || []).map(action => button(action[0].toUpperCase() + action.slice(1), () => controller.perform(async () => {
        if ((action === 'cancel' || action === 'retry') && !window.confirm(`${action === 'cancel' ? 'Cancel' : 'Retry'} this run? Completed outputs remain attached to their original run.`)) return
        const result = await controller.mutate('control', { action, expectedStatus: run.status }, run.id)
        await controller.loadRun(result.runId || run.id)
      }), { key: action, disabled: state.busy }))),
    h(Approval, { controller, state, run }),
    section('Steps', code(run.steps || [])), run.errors?.length ? section('Errors', code(run.errors)) : null,
    section('Events', h('ol', null, state.events.map((event, index) => h('li', { key: event.sequence || event.id || index }, `${event.occurredAt || event.at || ''} · ${event.message || event.type}`)))),
    section('Artifacts', h(ArtifactList, { controller, state, artifacts: state.artifacts })),
    run.lineage?.videoId ? button('Open source in ClipIt', () => ctxOpen(controller, state.status, `/editor?video=${encodeURIComponent(run.lineage.videoId)}`)) : null)
  return section('Runs',
    field('Search runs', h(Input, { value: search, onChange: e => setSearch(e.target.value) })),
    field('Status', h('select', { value: status, onChange: e => setStatus(e.target.value) },
      ...['', 'queued', 'running', 'paused', 'awaiting_approval', 'completed', 'failed', 'cancelled'].map(value => h('option', { key: value, value }, value || 'All statuses')))),
    button('Apply filters', () => controller.perform(() => controller.loadRuns({ search, status })), { disabled: state.busy }),
    state.runs.length ? h('ul', null, state.runs.map(item => h('li', { key: item.id, style: { marginBlock: 10 } },
      button(item.name || item.id, () => controller.select(item.id)), h('span', { style: { marginLeft: 10 } }, `${item.status} · ${item.progress || 0}%`)))) : h('p', null, 'No runs match this view.'),
    state.runsHasMore ? button('Load more runs', () => controller.perform(() => controller.loadRuns({ more: true, search, status })), { disabled: state.busy }) : null)
}

function Capabilities({ controller, state }) {
  const [query, setQuery] = useState(''), [tool, setTool] = useState(null), [parameters, setParameters] = useState('{}')
  const [preflight, setPreflight] = useState(null), [confirmed, setConfirmed] = useState(false), [result, setResult] = useState(null)
  const [videoId, setVideoId] = useState('')
  const request = () => ({ functionName: tool.name, parameters: JSON.parse(parameters), ...(videoId ? { videoId } : {}), confirmed })
  const change = value => { setParameters(value); setPreflight(null); setConfirmed(false) }
  const controls = tool?.parameters?.properties || {}
  return section('Live capabilities',
    field('Search tools', h(Input, { value: query, onChange: e => setQuery(e.target.value) })),
    h('div', { style: { maxHeight: 220, overflow: 'auto', display: 'flex', gap: 6, flexWrap: 'wrap' } },
      ...state.capabilities.filter(value => `${value.name} ${value.briefDescription || value.description || ''}`.toLowerCase().includes(query.toLowerCase())).map(value => button(value.name, () => controller.perform(async () => {
        const detail = await controller.call('tool', { id: value.name })
        setTool(detail.tool); change('{}'); setResult(null)
      }), { key: value.name, disabled: value.available === false }))),
    tool ? h('div', null, h('h3', null, tool.name), h('p', null, tool.description), code({ requiredPermissions: tool.requiredPermissions, missingPermissions: tool.missingPermissions, confirmation: tool.confirmation }),
      field('Video context ID (optional)', h(Input, { value: videoId, onChange: e => { setVideoId(e.target.value); setPreflight(null); setConfirmed(false) } })),
      ...Object.entries(controls).filter(([, schema]) => ['string', 'number', 'integer', 'boolean'].includes(schema.type)).map(([name, schema]) => {
        let parsed
        try { parsed = JSON.parse(parameters) } catch { parsed = {} }
        return field(name + (tool.parameters?.required?.includes(name) ? ' *' : ''), h(Input, {
          key: name, type: schema.type === 'boolean' ? 'checkbox' : ['number', 'integer'].includes(schema.type) ? 'number' : 'text',
          ...(schema.type === 'boolean' ? { checked: parsed[name] === true } : { value: parsed[name] ?? '' }),
          onChange: e => change(JSON.stringify({ ...parsed, [name]: schema.type === 'boolean' ? e.target.checked : ['number', 'integer'].includes(schema.type) ? Number(e.target.value) : e.target.value }, null, 2))
        }))
      }),
      field('Complete parameters (JSON; all fields preserved)', h(Textarea, { value: parameters, onChange: e => change(e.target.value), rows: 8 })),
      button('Preflight action', () => controller.perform(async () => { setPreflight(await controller.call('preflight', { body: { request: request() } })); setConfirmed(false) }), { disabled: state.busy }),
      preflight ? h('div', null, code(preflight), field('I approve this exact action, target and estimated cost.', h('input', { type: 'checkbox', checked: confirmed, onChange: e => setConfirmed(e.target.checked) })),
        button('Execute approved action', () => controller.perform(async () => {
          setResult(await controller.mutate('execute', { request: request(), ...(preflight.preflightId ? { preflightId: preflight.preflightId } : {}) }))
          setPreflight(null); setConfirmed(false)
        }), { disabled: state.busy || !confirmed || preflight.allowed === false })) : null,
      result ? section('Execution result', code(result)) : null) : h('p', null, 'Choose a tool to inspect its live schema, permissions and approval requirements.'))
}

function ctxOpen(_controller, status, path) {
  const base = new URL(status?.appOrigin || 'https://clipit.dev')
  if (!['https:', 'http:'].includes(base.protocol)) return
  return _controller.openExternal(new URL(path, base).href)
}

function RunLinks({ controller, runs }) {
  return runs.length ? h('ul', { style: { listStyle: 'none', padding: 0 } }, runs.map(run => h('li', { key: run.id, style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, padding: 12, borderBottom: '1px solid var(--ui-stroke-secondary)' } },
    button(run.name || run.id, async () => { await controller.tab('Runs'); await controller.select(run.id) }),
    h('span', null, `${run.status} · ${run.progress || 0}%`)))) : h('p', null, 'No active runs. Start with a source and a clear brief.')
}

function OverviewSummary({ controller, state }) {
  const overview = state.overview
  const stats = [['Available credits', overview?.credits?.balanceClip ?? 'Unavailable'], ['Active runs', overview?.runs?.length ?? 'Unavailable'], ['Approvals', overview?.approvals?.length ?? 'Unavailable']]
  return section('Your workspace',
    h('p', null, `Account ${state.status.accountId || 'unknown'} · ${overview?.billingMode === 'enterprise_usage_only' ? 'Enterprise usage' : 'Direct account'}`),
    overview?.status === 'degraded' ? h('p', { role: 'status' }, `Some information is temporarily unavailable: ${(overview.degraded || []).join(', ')}.`) : null,
    h('dl', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12, margin: 0 } }, stats.map(([label, value]) => h('div', { key: label, style: { padding: 16, border: '1px solid var(--ui-stroke-secondary)', borderRadius: 10 } },
      h('dt', { style: { color: 'var(--ui-text-secondary)', fontSize: 12 } }, localized(label)), h('dd', { style: { fontSize: 24, fontWeight: 600, margin: '8px 0 0' } }, String(value))))),
    (overview?.approvals || []).length ? section('Approvals', ...(overview.approvals || []).map(approval => button(`Review ${approval.runId}`, async () => { await controller.tab('Runs'); await controller.select(approval.runId) }, { key: approval.approvalId }))) : null)
}

function ControlRoom({ controller }) {
  const state = useSyncExternalStore(controller.subscribe, controller.snapshot)
  const profile = useValue(host.state.profile)
  const [doctor, setDoctor] = useState(null), [librarySearch, setLibrarySearch] = useState('')
  useEffect(() => controller.mount(), [controller])
  useEffect(() => { setDoctor(null); setLibrarySearch('') }, [profile])
  const compatible = state.status?.compatibility?.contractVersion === CONTRACT_VERSION
  return h('main', { 'aria-label': 'ClipIt Control Room', style: { padding: 24, maxWidth: 1100, margin: '0 auto', color: 'var(--ui-text-primary)', height: '100%', overflow: 'auto' } },
    h('header', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 } },
      h('div', null, h('h1', { style: { fontSize: 24, fontWeight: 650 } }, 'ClipIt'), h('p', { style: { color: 'var(--ui-text-secondary)' } }, 'Create, review and deliver with Clippy.')),
      button('Refresh', () => controller.perform(controller.refresh), { disabled: state.busy })),
    h('nav', { 'aria-label': 'ClipIt views', style: { display: 'flex', flexWrap: 'wrap', gap: 8, marginBlock: 18 } },
      ...TABS.map(tab => button(tab, () => controller.tab(tab), { key: tab, 'aria-current': state.tab === tab ? 'page' : undefined }))),
    state.busy ? h('p', { role: 'status', 'aria-live': 'polite' }, 'Loading ClipIt…') : null,
    state.error ? h('div', { role: 'alert', style: { padding: 14, border: '1px solid var(--ui-stroke-secondary)' } }, state.error) : null,
    !state.connected ? section('Connect ClipIt', h('p', null, 'Enable the ClipIt Python plugin on your gateway and set CLIPPER_API_KEY using Hermes’ hidden secret prompt. Enable this Desktop plugin separately. For a remote gateway, configure its profile environment.'),
      button('Retry connection', () => controller.perform(controller.refresh), { disabled: state.busy })) : null,
    state.connected && !compatible ? section('Server update required', h('p', null, 'This server supports the existing ClipIt clients but does not yet advertise the Control Room contract. Update the ClipIt server before starting native runs. Existing CLI, MCP and Python commands remain available.')) : null,
    h(Receipt, { controller, state }),
    state.connected && compatible && state.tab === 'Overview' ? h('div', null,
      h(OverviewSummary, { controller, state }),
      h(Intake, { key: state.status?.connectionId || profile, controller, state }),
      section('Recent activity', h(RunLinks, { controller, runs: state.overview?.runs || [] })),
      section('Outcome recipes', h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 8 } }, ...(state.recipes || []).map(recipe => button(recipe.name, () => controller.perform(async () => {
        const detail = await controller.call('skill', { id: recipe.id }); controller.showRecipe(detail)
      }), { key: recipe.id, disabled: state.busy }))), state.recipe ? code(state.recipe) : null)) : null,
    state.connected && compatible && state.tab === 'Runs' ? h(Runs, { key: state.status?.connectionId || profile, controller, state }) : null,
    state.connected && compatible && state.tab === 'Library' ? section('Library',
      field('Search artifacts', h(Input, { value: librarySearch, onChange: e => setLibrarySearch(e.target.value) })),
      button('Search library', () => controller.perform(() => controller.loadLibrary(false, librarySearch)), { disabled: state.busy }),
      h(ArtifactList, { key: state.status?.connectionId || profile, controller, state, artifacts: state.library }),
      state.libraryHasMore ? button('Load more artifacts', () => controller.perform(() => controller.loadLibrary(true, librarySearch)), { disabled: state.busy }) : null) : null,
    state.connected && compatible && state.tab === 'Capabilities' ? h(Capabilities, { key: state.status?.connectionId || profile, controller, state }) : null,
    state.tab === 'Settings' ? section('Connection and diagnostics', code(state.status),
      h('p', null, `Agent Pack ${VERSION} · Contract ${CONTRACT_VERSION} · Tested with Hermes v2026.9.14.`),
      h('p', null, 'Credentials stay in the gateway profile environment. Rotate or revoke them in ClipIt, then update the gateway secret and refresh. Uninstalling this plugin does not revoke a shared key.'),
      h('p', null, state.status?.compatibility?.features?.coordinatedPolling && state.status?.compatibility?.pollingMode !== 'manual' ? 'Background refresh shares a server quota across clients. It stops when the view closes or the selected run finishes. Open a run to refresh its exact approval and delivery details.' : 'Refresh is manual until this server advertises tested coordinated polling.'),
      button('Run Doctor', () => controller.perform(async () => setDoctor(await controller.doctor())), { disabled: state.busy }),
      doctor ? code(doctor) : null,
      button('Reset local upload checkpoint', () => { if (window.confirm('This removes only the local resume checkpoint. It cannot abort or undo a server upload. Check ClipIt first.')) { controller.saveUpload(null); void controller.perform(controller.refresh) } }, { disabled: state.busy }),
      button('Open ClipIt', () => ctxOpen(controller, state.status, '/'))) : null)
}

function Status({ controller }) {
  const state = useSyncExternalStore(controller.subscribe, controller.snapshot)
  const attention = state.runs.filter(run => ['awaiting_approval', 'failed'].includes(run.status)).length
  const active = state.runs.filter(run => !TERMINAL.has(run.status)).length
  if (!state.error && !attention && !active) return null
  return button(state.error ? 'ClipIt: connection needs attention' : `ClipIt: ${attention ? `${attention} need attention` : `${active} active`}`, () => host.navigate('/clipit'))
}

export default {
  id: 'clipit', name: 'ClipIt', defaultEnabled: false,
  register(ctx) {
    const controller = createController(ctx)
    ctx.i18n.register(LOCALES)
    controller.doctor = () => ctx.rest('/doctor', { timeoutMs: 45000 })
    controller.openExternal = url => ctx.os.openExternal(url)
    const unsubscribe = host.state.profile.subscribe(() => controller.profileChanged())
    if (typeof ctx.onDispose !== 'function') { unsubscribe(); controller.close(); throw new Error('Update Hermes to the tested Desktop SDK before enabling ClipIt.') }
    ctx.onDispose(() => { unsubscribe(); controller.close() })
    ctx.registerMany([
      { id: 'control-room', area: ROUTES_AREA, data: { path: '/clipit' }, render: () => h(ControlRoom, { controller }) },
      { id: 'navigation', area: SIDEBAR_NAV_AREA, data: { path: '/clipit', label: 'ClipIt', codicon: 'play-circle' } },
      { id: 'status', area: STATUSBAR_AREAS.right, render: () => h(Status, { controller }) },
      ...[['open', 'Open ClipIt', 'Overview'], ['start', 'Start a ClipIt run', 'Overview'], ['runs', 'Open ClipIt runs', 'Runs'], ['approvals', 'Review ClipIt approvals', 'Runs']].map(([id, label, tab]) => ({
        id, area: PALETTE_AREA, data: { id: `clipit.${id}`, label, keywords: ['clipit', 'clippy', 'video'], run: () => {
          host.navigate('/clipit'); void controller.tab(tab).then(() => id === 'approvals' ? controller.perform(() => controller.loadRuns({ status: 'awaiting_approval' })) : undefined)
        } }
      })),
      { id: 'activity', area: PANES_AREA, title: 'ClipIt activity', data: { placement: 'right', width: '320px' }, render: () => h(Status, { controller }) },
      { id: 'attach-run', area: COMPOSER_AREAS.attachments, data: { label: 'ClipIt run reference', icon: 'play-circle', run: target => {
        const run = controller.snapshot().selected
        if (run?.id && /^[a-zA-Z0-9_-]{1,128}$/.test(run.id)) target.insertText(`ClipIt run reference: ${run.id}`)
        else { host.navigate('/clipit'); void controller.tab('Runs') }
      } } }
    ])
  }
}
