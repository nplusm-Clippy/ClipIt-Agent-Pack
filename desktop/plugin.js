import { createElement as h, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { host, useValue, usePluginI18n, Button, Input, Textarea, ROUTES_AREA, SIDEBAR_NAV_AREA,
  STATUSBAR_AREAS, PALETTE_AREA, PANES_AREA, COMPOSER_AREAS } from '@hermes/plugin-sdk'

export const VERSION = '3.1.0'
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
const mergeRows = (previous, incoming, key = 'id', limit = 500) => [...new Map([...previous, ...incoming].map(row => [row[key], row])).values()].slice(-limit)
const mergeEvents = (previous, incoming) => [...new Map([...previous, ...incoming].map(event => [event.sequence ?? event.id ?? `${event.occurredAt}:${event.message}`, event])).values()].slice(-1000)
const confirmedControls = (controls, run) => {
  const next = { ...controls }, action = next[run.id]
  if ((action === 'pause' && run.status === 'paused') || (action === 'cancel' && run.status === 'cancelled') || (action === 'resume' && ['queued', 'running', 'processing'].includes(run.status)) || TERMINAL.has(run.status)) delete next[run.id]
  return next
}
const modeKey = () => `control-room-mode:${host.state.profile.get()}`

export function createController(ctx) {
  const initial = () => ({ status: null, tab: 'Overview', runs: [], library: [], capabilities: [], recipes: [], overview: null,
    selected: null, showDetail: false, events: [], artifacts: [], error: null, busy: false, loading: false, receipt: null, uploadReceipt: null, sourceImport: null, connected: false,
    uiMode: ctx.storage.get(modeKey(), 'modern') === 'classic' ? 'classic' : 'modern', lastSuccessAt: null, connectionError: null,
    runFilters: { status: '', search: '' }, libraryFilters: { search: '', status: '', kind: '' }, resources: [], resourceQuery: {}, controlRequests: {}, changeDraft: '' })
  let state = initial()
  let closed = false, generation = 0, views = 0, timer = null, activeTask = null
  let pollDelay = 5000, selectionRequest = 0, listRequest = 0, libraryRequest = 0, resourceRequest = 0, reads = 0
  let resourceCursor = null, resourceOffset = 0
  let scope = '', nextCursor = null, eventCursor = null, artifactCursor = null, libraryCursor = null, refreshFlight = null
  const listeners = new Set(), seen = new Map()
  const update = change => {
    if (closed) return
    state = { ...state, ...change }
    listeners.forEach(fn => fn())
  }
  const call = async (operation, arguments_ = {}) => {
    if (closed) throw new Error('ClipIt is disabled.')
    const epoch = generation
    try {
      const result = await ctx.rest(`/operations/${operation}`, { method: 'POST', body: { ...arguments_, connectionId: state.status?.connectionId }, timeoutMs: 65000 })
      if (closed || epoch !== generation) throw new Error('The ClipIt connection changed. Refresh before continuing.')
      if (result?.ok === false) throw Object.assign(new Error(result.error?.message || 'ClipIt request failed.'), { details: result.error })
      update({ lastSuccessAt: new Date().toISOString() })
      return result
    } catch (error) {
      if (!closed && epoch === generation && (!error.details || error.details.status >= 500 || error.details.status === 401)) update({ connectionError: error.message || 'Connection unavailable.' })
      throw error
    }
  }
  const read = async task => {
    const epoch = generation
    reads += 1; update({ loading: true })
    try { return await task() }
    catch (error) { if (!closed && epoch === generation) update({ error: error.message || 'Could not refresh ClipIt.' }); return null }
    finally { if (epoch === generation) { reads = Math.max(0, reads - 1); update({ loading: reads > 0 }) } }
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
  }
  const loadRun = async (id, append = false) => {
    const request = ++selectionRequest
    const epoch = generation
    const result = await call('run', { id })
    if (epoch !== generation || closed || request !== selectionRequest) return
    const run = result.run || result
    const changed = state.selected?.id !== run.id
    if (!append || changed) eventCursor = null
    update({ selected: run, showDetail: true, controlRequests: confirmedControls(state.controlRequests, run), ...(changed ? { changeDraft: '' } : {}), ...(!append || changed ? { events: [], artifacts: [] } : {}) })
    notify(run)
    const events = await call('events', { id, query: { limit: 100, ...(append && eventCursor ? { cursor: eventCursor } : {}) } })
    if (epoch !== generation || closed || state.selected?.id !== id || request !== selectionRequest) return
    eventCursor = events.page?.resumeCursor || events.page?.nextCursor || eventCursor
    update({ events: mergeEvents(append ? state.events : [], items(events)), eventsHasMore: !!events.page?.hasMore })
    const artifacts = await call('artifacts', { id, query: { limit: 100 } })
    if (epoch === generation && !closed && state.selected?.id === id && request === selectionRequest) { artifactCursor = artifacts.page?.nextCursor; update({ artifacts: items(artifacts), artifactsHasMore: !!artifactCursor }) }
  }
  const loadRuns = async ({ more = false, status, search } = {}) => {
    const epoch = generation, request = ++listRequest
    const filters = { status: status ?? state.runFilters.status, search: search ?? state.runFilters.search }
    update({ runFilters: filters })
    const data = await call('runs', { query: { limit: 50, ...(more && nextCursor ? { cursor: nextCursor } : {}), ...(filters.status ? { status: filters.status } : {}), ...(filters.search ? { search: filters.search } : {}) } })
    if (epoch !== generation || closed || request !== listRequest) return
    nextCursor = data.page?.nextCursor
    items(data).forEach(notify)
    update({ runs: mergeRows(more ? state.runs : [], items(data)), runsHasMore: !!nextCursor })
  }
  const loadLibrary = async (more = false, search = state.libraryFilters.search, filters = {}) => {
    const epoch = generation, request = ++libraryRequest
    const nextFilters = { ...state.libraryFilters, ...filters, search }
    update({ libraryFilters: nextFilters })
    const data = await call('library', { query: { limit: 50, ...(more && libraryCursor ? { cursor: libraryCursor } : {}),
      ...Object.fromEntries(Object.entries(nextFilters).filter(([, value]) => value)) } })
    if (epoch !== generation || closed || request !== libraryRequest) return
    libraryCursor = data.page?.nextCursor
    update({ library: mergeRows(more ? state.library : [], items(data)), libraryHasMore: !!libraryCursor })
  }
  const loadResources = async ({ search = '', kind = 'video', more = false } = {}) => {
    const epoch = generation, request = ++resourceRequest
    const supported = state.status?.compatibility?.features?.resourceSearch === true
    update({ resourceQuery: { search, kind }, resourceSearchSupported: supported })
    if (!supported && kind !== 'video') { update({ resources: [], resourcesHasMore: false }); return }
    const data = supported ? await call('resources', { query: { kind, search, limit: 20, ...(more && resourceCursor ? { cursor: resourceCursor } : {}) } })
      : await call('videos', { query: { limit: 20, offset: more ? resourceOffset : 0 } })
    if (epoch !== generation || closed || request !== resourceRequest) return
    resourceCursor = data.page?.nextCursor
    resourceOffset = (more ? resourceOffset : 0) + items(data).length
    const rows = items(data).map(item => ({ ...item, kind: item.kind || 'video', label: item.label || item.title || item.originalFilename || 'Untitled source', status: item.status || item.processingStatus }))
    update({ resources: mergeRows(more ? state.resources : [], rows), resourcesHasMore: supported ? !!resourceCursor : resourceOffset < (data.total || 0) })
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
        reads = 0; activeTask = null; update({ loading: false, busy: false })
        seen.clear(); nextCursor = null; libraryCursor = null; eventCursor = null
        selectionRequest += 1; listRequest += 1; libraryRequest += 1; resourceRequest += 1; resourceCursor = null; resourceOffset = 0
        update({ runs: [], selected: null, library: [], events: [], artifacts: [], capabilities: [], recipes: [], recipe: null, overview: null, sourceImport: null, recovery: null, resources: [], controlRequests: {}, changeDraft: '' })
      }
      scope = nextScope
      const rawReceipt = ctx.storage.get(`receipt:${scope}`, null)
      const saved = rawReceipt && rawReceipt.version === 1 && typeof rawReceipt.pending === 'boolean' && /^[a-zA-Z0-9_.:-]{8,128}$/.test(rawReceipt.idempotencyKey || '') ? rawReceipt : rawReceipt ? { version: 1, pending: true, corrupt: true } : null
      const rawUpload = ctx.storage.get(`upload:${scope}`, null)
      const upload = rawUpload && rawUpload.version === 1 && /^[a-zA-Z0-9_.:-]{8,128}$/.test(rawUpload.idempotencyKey || '') && typeof rawUpload.file?.name === 'string' && Number.isSafeInteger(rawUpload.file?.size) && rawUpload.partHashes && Object.keys(rawUpload.partHashes).length <= 10000 ? rawUpload : null
      if (rawUpload && !upload) throw new Error('Saved upload metadata is invalid. Inspect your uploads in ClipIt before resetting this plugin’s local state.')
      update({ status: connection, connected: true, error: null, connectionError: null, lastSuccessAt: new Date().toISOString(), receipt: saved?.version === 1 ? saved : null, uploadReceipt: upload?.version === 1 ? upload : null })
      if (connection.compatibility?.contractVersion !== CONTRACT_VERSION) return
      if (state.tab === 'Runs') await loadRuns()
      else if (state.tab === 'Library') await loadLibrary()
      else if (state.tab === 'Capabilities') {
        const data = await call('catalog')
        if (epoch === generation && !closed) update({ capabilities: items(data) })
      } else if (state.tab === 'Overview') {
        const data = await call('overview')
        if (state.uiMode === 'classic') {
          const recipes = await call('recipes')
          if (epoch === generation && !closed) update({ overview: data, recipes: items(recipes) })
        } else {
          if (epoch === generation && !closed) update({ overview: data })
          await loadRuns()
        }
      }
    })().catch(error => { if (!closed && epoch === generation) update({ connectionError: error.message || 'Connection unavailable.' }); throw error })
      .finally(() => { if (refreshFlight === flight) refreshFlight = null })
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
    if (state.connectionError) throw new Error('Refresh the connection before taking another action.')
    const key = crypto.randomUUID()
    const receipt = { operation, id: id || null, action: body.action || null, idempotencyKey: key, pending: true }
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
    const delay = Math.max(pollDelay, document.hidden ? 60000 : state.status.compatibility.limits?.recommendedPollSeconds * 1000 || 5000)
    timer = setTimeout(async () => {
      timer = null
      if (activeTask || refreshFlight) { schedule(); return }
      const epoch = generation, selection = selectionRequest, selectedId = state.selected && !TERMINAL.has(state.selected.status) ? state.selected.id : null
      try {
        const snapshot = await call('poll_budget', { body: { runIds: state.runs.slice(0, 50).map(run => run.id), ...(selectedId ? { runId: selectedId } : {}), ...(selectedId && eventCursor ? { cursor: eventCursor } : {}) } })
        if (epoch !== generation || closed || views === 0) return
        pollDelay = Math.max(5000, snapshot.intervalMs || snapshot.retryAfterSeconds * 1000 || 5000, Date.parse(snapshot.nextPollAt || '') - Date.now() || 0)
        update({ overview: snapshot.overview, connectionError: null })
        ;[...(snapshot.overview?.runs || []), ...(snapshot.runs || [])].forEach(notify)
        if (state.tab === 'Runs' || state.tab === 'Overview') {
          const changes = new Map((snapshot.runs || []).map(run => [run.id, run]))
          update({ runs: state.runs.map(run => changes.has(run.id) ? { ...run, ...changes.get(run.id) } : run) })
        }
        if (snapshot.run && selection === selectionRequest && state.selected?.id === snapshot.run.id) {
          const run = { ...state.selected, ...snapshot.run }
          if (snapshot.run.status !== state.selected.status) { run.currentApproval = null; run.allowedControls = []; run.detailNeedsRefresh = true }
          update({ selected: run, controlRequests: confirmedControls(state.controlRequests, run) })
          notify(run)
          if (snapshot.events) {
            eventCursor = snapshot.events.page?.resumeCursor || eventCursor
            update({ events: mergeEvents(state.events, items(snapshot.events)), eventsHasMore: !!snapshot.events.page?.hasMore })
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
    call, read, perform, mutate, recover, refresh, loadRuns, loadLibrary, loadRun, loadResources,
    async setMode(mode) { ctx.storage.set(modeKey(), mode === 'classic' ? 'classic' : 'modern'); update({ uiMode: mode, tab: 'Overview' }); await read(refresh); schedule() },
    saveChangeDraft(value) { update({ changeDraft: value }) },
    async respondToApproval(run, approval, decision) {
      const result = await call('run', { id: run.id }), fresh = result.run || result
      const current = fresh.currentApproval
      if (fresh.status !== 'awaiting_approval' || current?.approvalId !== approval.approvalId || current?.actionDigest !== approval.actionDigest || !Number.isFinite(Date.parse(current?.expiresAt)) || Date.parse(current.expiresAt) <= Date.now()) {
        if (state.selected?.id === run.id) update({ selected: fresh })
        throw new Error('The approval changed or expired. Review the current plan before deciding.')
      }
      const response = await mutate('approval', { approvalId: approval.approvalId, actionDigest: approval.actionDigest, decision }, run.id)
      if (response?.runId) { update({ tab: 'Runs' }); await loadRun(response.runId) }
      return response
    },
    async control(run, action) {
      const result = await call('run', { id: run.id }), fresh = result.run || result
      if (fresh.status !== run.status || !fresh.allowedControls?.includes(action)) {
        if (state.selected?.id === run.id) update({ selected: fresh })
        throw new Error('This workflow changed. Review its current controls before acting.')
      }
      update({ controlRequests: { ...state.controlRequests, [run.id]: action } })
      try {
        const response = await mutate('control', { action, expectedStatus: fresh.status }, run.id)
        if (response?.runId) await loadRun(response.runId)
        return response
      } catch (error) {
        if (!state.receipt?.pending) { const controls = { ...state.controlRequests }; delete controls[run.id]; update({ controlRequests: controls }) }
        throw error
      }
    },
    async moreEvents() {
      const id = state.selected?.id, selection = selectionRequest
      if (!id || !eventCursor) return
      const data = await call('events', { id, query: { cursor: eventCursor, limit: 100 } })
      if (state.selected?.id !== id || selection !== selectionRequest) return
      eventCursor = data.page?.resumeCursor || data.page?.nextCursor || eventCursor
      update({ events: mergeEvents(state.events, items(data)), eventsHasMore: !!data.page?.hasMore })
    },
    async moreArtifacts() {
      const id = state.selected?.id, selection = selectionRequest
      if (!id || !artifactCursor) return
      const data = await call('artifacts', { id, query: { cursor: artifactCursor, limit: 100 } })
      if (state.selected?.id !== id || selection !== selectionRequest) return
      artifactCursor = data.page?.nextCursor
      update({ artifacts: mergeRows(state.artifacts, items(data)), artifactsHasMore: !!artifactCursor })
    },
    showRecipe(recipe) { update({ recipe }) },
    requestBrief() { update({ requestedDialog: 'brief' }) },
    consumeDialog() { update({ requestedDialog: null }) },
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
    mount() { views += 1; read(refresh).then(schedule); return () => { views -= 1; if (views === 0) stopPolling() } },
    async tab(tab) { update({ tab, error: null, ...(tab === 'Library' && state.uiMode !== 'classic' ? { libraryFilters: { ...state.libraryFilters, role: 'output' } } : {}) }); await read(refresh); schedule() },
    async select(id) { eventCursor = null; await read(() => loadRun(id)); schedule() },
    async openRun(id) { update({ tab: 'Runs' }); eventCursor = null; await loadRun(id); schedule() },
    showActivityList() { update({ showDetail: false }) },
    clearSelected() { selectionRequest += 1; update({ selected: null, showDetail: false, events: [], artifacts: [] }); eventCursor = null; schedule() },
    profileChanged() {
      generation += 1; scope = ''; seen.clear(); stopPolling(); refreshFlight = null; activeTask = null; pollDelay = 5000; reads = 0
      selectionRequest += 1; listRequest += 1; libraryRequest += 1; resourceRequest += 1; resourceCursor = null; resourceOffset = 0
      state = initial()
      listeners.forEach(fn => fn())
      if (views) read(refresh).then(schedule)
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

function ClassicControlRoom({ controller }) {
  const state = useSyncExternalStore(controller.subscribe, controller.snapshot)
  const profile = useValue(host.state.profile)
  const [doctor, setDoctor] = useState(null), [librarySearch, setLibrarySearch] = useState('')
  useEffect(() => controller.mount(), [controller])
  useEffect(() => { setDoctor(null); setLibrarySearch('') }, [profile])
  const compatible = state.status?.compatibility?.contractVersion === CONTRACT_VERSION
  return h('main', { 'aria-label': 'ClipIt Control Room', style: { padding: 24, maxWidth: 1100, margin: '0 auto', color: 'var(--ui-text-primary)', height: '100%', overflow: 'auto' } },
    h('header', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 } },
      h('div', null, h('h1', { style: { fontSize: 24, fontWeight: 650 } }, 'ClipIt'), h('p', { style: { color: 'var(--ui-text-secondary)' } }, 'Create, review and deliver with Clippy.')),
      h('div', null, button('Try new Control Room', () => controller.setMode('modern')), button('Refresh', () => controller.perform(controller.refresh), { disabled: state.busy }))),
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
      h('p', null, state.status?.compatibility?.features?.coordinatedPolling && state.status?.compatibility?.pollingMode !== 'manual' ? 'Background refresh shares a server quota across clients. It stops when the view closes. Completed selections do not stop other activity updates. Open a run to refresh its exact approval and delivery details.' : 'Refresh is manual until this server advertises tested coordinated polling.'),
      button('Run Doctor', () => controller.perform(async () => setDoctor(await controller.doctor())), { disabled: state.busy }),
      doctor ? code(doctor) : null,
      button('Reset local upload checkpoint', () => { if (window.confirm('This removes only the local resume checkpoint. It cannot abort or undo a server upload. Check ClipIt first.')) { controller.saveUpload(null); void controller.perform(controller.refresh) } }, { disabled: state.busy }),
      button('Open ClipIt', () => ctxOpen(controller, state.status, '/'))) : null)
}

const friendly = value => String(value || 'Unknown').replace(/([a-z])([A-Z])/g, '$1 $2').replaceAll('_', ' ').replace(/^./, char => char.toUpperCase())
const runName = run => run?.name || 'Untitled workflow'
const runState = status => ({ awaiting_approval: 'Needs your approval', running: 'Working', processing: 'Working', queued: 'Queued', paused: 'Paused', completed: 'Finished', failed: 'Needs help', cancelled: 'Cancelled' })[status] || friendly(status)
const activityMessage = event => event.presentation?.message || ({ status_changed: 'Workflow status updated.', approval_requested: 'A decision was requested.' })[event.type] || 'Workflow activity recorded. Detailed history is unavailable.'
const dateLabel = value => value && Number.isFinite(Date.parse(value)) ? new Date(value).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : 'Time unavailable'
const durationLabel = seconds => Number.isFinite(seconds) ? `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}` : null
const outputName = item => item.presentation?.label || item.label || `${friendly(item.kind)} reference`
const actionable = state => state.connected && !state.connectionError && !state.busy && !state.receipt?.pending && state.status?.compatibility?.contractVersion === CONTRACT_VERSION
const crButton = (label, onClick, props = {}) => h('button', { type: 'button', className: 'cr-button', onClick, ...props }, label)
const badge = (label, attention = false) => h('span', { className: `cr-badge${attention ? ' attention' : ''}` }, label)
const technical = value => h('details', { className: 'cr-technical' }, h('summary', null, 'Technical details'), code(value))
function appLink(controller, status, value) {
  try {
    const origin = new URL(status?.appOrigin || 'https://clipit.dev').origin
    const target = new URL(value, origin)
    if (target.origin !== origin || !['https:', 'http:'].includes(target.protocol) || target.username || target.password) return
    controller.openExternal(target.href)
  } catch { /* Unrecognized references are not opened. */ }
}
export function changeContext(run, artifacts, request = '') {
  return [`ClipIt workflow: ${runName(run)}`, `State: ${runState(run?.status)}`, run?.presentation?.source?.label ? `Source: ${run.presentation.source.label}` : '',
    artifacts.filter(item => item.presentation?.role === 'output').length ? `Outputs: ${artifacts.filter(item => item.presentation?.role === 'output').map(outputName).join(', ')}` : '',
    request ? `Requested change: ${request}` : '', `Internal task reference: ${run?.id || 'unavailable'}`, 'This is a draft for discussion; it does not interrupt or change the workflow.'].filter(Boolean).join('\n')
}
const CONTROL_STYLE = `
.clipit-control-room{--cr-line:var(--ui-stroke-secondary,#383b3e);--cr-muted:var(--ui-text-secondary,#9ba3a7);--cr-bg:var(--ui-bg-editor,var(--ui-bg-elevated,#202225));--cr-raised:var(--ui-bg-secondary,var(--ui-bg-primary,#25282a));--cr-accent:var(--ui-text-success,#97d9c0);color:var(--ui-text-primary,#edf1ef);font:14px/1.55 system-ui,sans-serif;height:100%;overflow:auto;container-type:inline-size;padding:24px;box-sizing:border-box}
.clipit-control-room *{box-sizing:border-box}.clipit-control-room h1,.clipit-control-room h2,.clipit-control-room h3,.clipit-control-room p{margin:0}.clipit-control-room h1{font-size:22px;letter-spacing:-.5px;font-weight:650}.clipit-control-room h2{font-size:24px;line-height:1.25;letter-spacing:-.5px}.clipit-control-room h3{font-size:15px;font-weight:650}.clipit-control-room p+p{margin-top:8px}.clipit-control-room .cr-muted{color:var(--cr-muted)}.clipit-control-room .cr-small{font-size:12px}.clipit-control-room .cr-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.clipit-control-room .cr-spread{justify-content:space-between}.clipit-control-room .cr-stack{display:grid;gap:16px}.clipit-control-room .cr-header{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:24px}.clipit-control-room .cr-header>div{min-width:0}.clipit-control-room .cr-header h1{overflow-wrap:anywhere}.clipit-control-room .cr-nav{display:flex;align-items:center;gap:24px;border-bottom:1px solid var(--cr-line);margin-bottom:24px}.clipit-control-room .cr-nav button{border:0;background:none;color:var(--cr-muted);padding:12px 0;border-bottom:2px solid transparent;font:inherit;cursor:pointer}.clipit-control-room .cr-nav button[aria-current=page]{color:var(--ui-text-primary,#edf1ef);border-color:var(--cr-accent)}.clipit-control-room .cr-button{font:inherit;font-size:13px;font-weight:550;border:1px solid var(--cr-line);border-radius:7px;padding:8px 12px;background:transparent;color:inherit;cursor:pointer;white-space:normal;max-width:100%;overflow-wrap:anywhere}.clipit-control-room .cr-button.primary{background:var(--cr-accent);border-color:transparent;color:#132d23}.clipit-control-room .cr-button.quiet{border-color:transparent}.clipit-control-room button:disabled{cursor:default;opacity:.48}.clipit-control-room :is(button,input,textarea,select,a,summary):focus-visible{outline:2px solid var(--cr-accent);outline-offset:3px}.clipit-control-room input:not([type=checkbox]):not([type=file]),.clipit-control-room textarea,.clipit-control-room select{display:block;width:100%;min-width:0;color:inherit;background:var(--cr-bg);border:1px solid var(--cr-line);border-radius:7px;padding:9px 10px;font:inherit}.clipit-control-room input[type=file]{max-width:100%}.clipit-control-room textarea{resize:vertical;min-height:100px}.clipit-control-room label{display:grid;gap:6px}.clipit-control-room .cr-checkbox{display:flex;align-items:flex-start;gap:10px}.clipit-control-room .cr-split{display:grid;grid-template-columns:minmax(230px,30%) minmax(0,1fr);gap:28px;align-items:start}.clipit-control-room .cr-list{list-style:none;margin:0;padding:0;display:grid;gap:4px;max-height:65vh;overflow:auto}.clipit-control-room .cr-task{width:100%;text-align:left;border:1px solid transparent;border-radius:8px;padding:14px 12px;background:transparent;color:inherit;cursor:pointer;display:grid;gap:6px;font:inherit}.clipit-control-room .cr-task[aria-current=true]{background:var(--cr-raised);border-color:var(--cr-line)}.clipit-control-room .cr-task strong{font-weight:550;overflow-wrap:anywhere}.clipit-control-room .cr-badge{font-size:11px;letter-spacing:.02em;color:var(--cr-muted);display:inline-flex;align-items:center;gap:5px}.clipit-control-room .cr-badge:before{content:'';width:5px;height:5px;flex-shrink:0;border-radius:50%;background:currentColor}.clipit-control-room .cr-badge.attention{color:var(--ui-text-warning,#d6ad6c)}.clipit-control-room .cr-panel{border:1px solid var(--cr-line);border-radius:10px;padding:20px;display:grid;gap:12px;min-width:0;overflow-wrap:anywhere}.clipit-control-room .cr-attention{border-left:3px solid var(--ui-text-warning,#d6ad6c)}.clipit-control-room .cr-detail{min-width:0;display:grid;gap:24px;padding-left:26px;border-left:1px solid var(--cr-line)}.clipit-control-room .cr-detail>section{display:grid;gap:12px}.clipit-control-room .cr-timeline{list-style:none;margin:0;padding:0;display:grid;gap:18px}.clipit-control-room .cr-timeline li{display:grid;grid-template-columns:8px minmax(0,1fr);gap:12px}.clipit-control-room .cr-timeline li:before{content:'';width:6px;height:6px;border-radius:50%;background:var(--cr-muted);margin-top:8px}.clipit-control-room .cr-timeline p{overflow-wrap:anywhere}.clipit-control-room .cr-output-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(180px,100%),1fr));gap:12px}.clipit-control-room .cr-output{padding:0;overflow:hidden;text-align:left;display:grid;align-content:start;gap:0}.clipit-control-room .cr-preview{height:105px;display:grid;place-items:center;color:var(--cr-muted);background:var(--cr-raised);border-bottom:1px solid var(--cr-line);font-size:12px}.clipit-control-room .cr-output-info{padding:14px;display:grid;gap:8px}.clipit-control-room .cr-banner{padding:14px 16px;background:var(--cr-raised);border:1px solid var(--cr-line);border-radius:8px;margin-bottom:16px}.clipit-control-room .cr-technical{font-size:12px;color:var(--cr-muted);overflow-wrap:anywhere}.clipit-control-room summary{cursor:pointer}.clipit-control-room .cr-empty{padding:48px 16px;text-align:center;display:grid;justify-items:center;gap:12px;color:var(--cr-muted)}.clipit-control-room .cr-back{display:none}.clipit-control-room dialog{width:min(660px,calc(100% - 32px));max-height:calc(100% - 48px);overflow:auto;background:var(--cr-bg);color:inherit;border:1px solid var(--cr-line);border-radius:12px;padding:24px;box-shadow:0 20px 80px #0005}.clipit-control-room dialog::backdrop{background:#0007}.clipit-control-room dialog>.cr-stack{margin-top:24px}.clipit-control-room dialog h2{font-size:21px}.clipit-control-room dl{display:grid;grid-template-columns:minmax(100px,30%) minmax(0,1fr);gap:8px 16px;margin:0}.clipit-control-room dt{color:var(--cr-muted)}.clipit-control-room dd{margin:0;overflow-wrap:anywhere}.clipit-control-room video{display:block;width:100%;max-height:400px}.clipit-control-room .cr-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
@container(max-width:820px){.clipit-control-room .cr-split{grid-template-columns:minmax(0,1fr)}.clipit-control-room .cr-split.has-selection .cr-queue{display:none}.clipit-control-room .cr-split:not(.has-selection) .cr-detail{display:none}.clipit-control-room .cr-detail{border:0;padding:0}.clipit-control-room .cr-back{display:inline-flex}.clipit-control-room .cr-header{gap:8px}.clipit-control-room .cr-header h1{font-size:20px}}
@media(prefers-reduced-motion:reduce){.clipit-control-room *{scroll-behavior:auto!important;transition:none!important}}
`
function ControlDialog({ title, onClose, children }) {
  const ref = useRef(null), returnFocus = useRef(null), close = useRef(onClose)
  close.current = onClose
  useEffect(() => {
    returnFocus.current = document.activeElement
    const dialog = ref.current
    if (typeof dialog.showModal === 'function') dialog.showModal()
    else dialog.setAttribute('open', '')
    return () => {
      if (dialog.open && typeof dialog.close === 'function') dialog.close()
      if (returnFocus.current?.isConnected) returnFocus.current.focus()
      else document.querySelector('.clipit-control-room h2[tabindex]')?.focus()
    }
  }, [])
  return h('dialog', { ref, 'aria-label': title, onCancel: event => { event.preventDefault(); close.current() } },
    h('div', { className: 'cr-row cr-spread' }, h('h2', null, title), crButton('Close', onClose, { 'aria-label': `Close ${title}` })), children)
}
function OutputCards({ values, onReview }) {
  return values.length ? h('div', { className: 'cr-output-grid' }, ...values.map(item => h('button', { key: item.id, type: 'button', className: 'cr-button cr-output', onClick: () => onReview(item) },
    h('span', { className: 'cr-preview' }, item.kind === 'clip' ? 'Select to inspect exports' : 'Preview unavailable'),
    h('span', { className: 'cr-output-info' }, h('strong', null, outputName(item)), badge(friendly(item.presentation?.readiness || 'unknown')), item.presentation?.sourceLabel ? h('span', { className: 'cr-small cr-muted' }, item.presentation.sourceLabel) : null)))) : h('p', { className: 'cr-muted' }, 'No confirmed outputs in this view yet.')
}
function ExactOutput({ controller, state, item, onClose }) {
  const [delivery, setDelivery] = useState(null), [exportId, setExportId] = useState(''), [media, setMedia] = useState(null), [preview, setPreview] = useState(false), [error, setError] = useState(''), [loading, setLoading] = useState(false)
  const alive = useRef(true), request = useRef(0)
  useEffect(() => () => { alive.current = false; request.current += 1 }, [])
  const clipId = item.resourceId || item.resourceRef?.id
  const task = async fn => { setLoading(true); setError(''); try { await fn() } catch (err) { if (alive.current) setError(err.message) } finally { if (alive.current) setLoading(false) } }
  const inspect = () => task(async () => {
    const token = ++request.current; setMedia(null); setPreview(false)
    const value = await controller.call('delivery_state', { id: clipId })
    if (alive.current && request.current === token) { setDelivery(value); setExportId(value.selectedExport?.exportId || '') }
  })
  const prepare = previewing => task(async () => {
    const token = ++request.current, selected = exportId
    setMedia(null); setPreview(false)
    const current = await controller.call('delivery_state', { id: clipId, query: { exportId: selected } })
    const exact = current.selectedExport
    if (current.selection?.selectedExportId !== selected || exact?.exportId !== selected || !exact.exactlyMatchesEditor || exact.inspectionStatus !== 'verified' || exact.blockers?.length) throw new Error('This export is not verified against the current edit. Inspect the current versions before continuing.')
    const download = await controller.call('download', { id: clipId, query: { exportId: selected } })
    const url = new URL(download.downloadUrl || download.url)
    if (url.protocol !== 'https:' || url.username || url.password || download.exportId !== selected) throw new Error('The exact export could not be verified.')
    if (download.expiresAt && (!Number.isFinite(Date.parse(download.expiresAt)) || Date.parse(download.expiresAt) <= Date.now())) throw new Error('The download link expired. Check this exact export again.')
    if (alive.current && token === request.current) { setDelivery(current); setMedia({ url: url.href, exportId: selected, expiresAt: download.expiresAt }); setPreview(previewing); if (!previewing) controller.openExternal(url.href) }
  })
  return h(ControlDialog, { title: outputName(item), onClose }, h('div', { className: 'cr-stack' },
    h('div', { className: 'cr-row' }, badge(friendly(item.presentation?.readiness)), item.presentation?.durationSeconds != null ? h('span', { className: 'cr-muted' }, durationLabel(item.presentation.durationSeconds)) : null),
    h('p', { className: 'cr-muted' }, 'A workflow result is not a recorded human review. Export verification checks the selected version against the current edit.'),
    item.presentation?.appUrl ? crButton('Open in ClipIt', () => appLink(controller, state.status, item.presentation.appUrl)) : null,
    item.kind === 'clip' && clipId ? crButton('Inspect available exports', inspect, { disabled: loading || !!state.connectionError }) : h('p', null, 'A media preview is not available for this resource.'),
    delivery ? h('div', { className: 'cr-stack' }, h('p', null, delivery.guidance || 'Choose a specific export version.'),
      field('Export version', h('select', { value: exportId, onChange: e => { request.current += 1; setExportId(e.target.value); setMedia(null); setPreview(false) } },
        h('option', { value: '' }, 'Choose an export'), ...(delivery.exports || []).map((value, index) => h('option', { key: value.exportId, value: value.exportId }, [`Version ${index + 1}`, value.format?.toUpperCase(), value.width && value.height ? `${value.width} × ${value.height}` : null, value.editorVersion != null ? `Edit ${value.editorVersion}` : null].filter(Boolean).join(' · '))))),
      delivery.deliveryBlockers?.length ? h('p', null, delivery.deliveryBlockers.map(friendly).join(' · ')) : null,
      h('div', { className: 'cr-row' }, crButton('Preview exact export', () => prepare(true), { disabled: loading || !exportId || !!state.connectionError }), crButton('Download exact export', () => prepare(false), { disabled: loading || !exportId || !!state.connectionError }))) : null,
    error ? h('p', { role: 'alert' }, error) : null,
    preview && media ? h('video', { src: media.url, controls: true, preload: 'metadata', 'aria-label': 'Exact export preview', onError: () => { setMedia(null); setPreview(false); setError('Preview unavailable or link expired. Check the same exact export again.') } }) : null,
    technical({ artifact: item, delivery, selectedExportId: exportId })))
}
function readableActionValue(key, value, run, artifacts) {
  if (/^(clip|video|project|sequence|export|snapshot|task|resource|account|workspace|user|generation|job)Ids?$/i.test(key)) {
    if (Array.isArray(value)) return value.map(item => readableActionValue(key.replace(/s$/, ''), item, run, artifacts)).join(', ')
    if (run.presentation?.source?.id === value) return run.presentation.source.label
    const target = run.currentApproval?.presentation?.targets?.find(item => item.id === value)
    if (target?.label) return target.label
    const known = artifacts.find(item => (item.resourceId || item.resourceRef?.id) === value)
    return known ? outputName(known) : `${friendly(key.replace(/Ids?$/, ''))} reference (see technical details)`
  }
  if (value && typeof value === 'object') return text(Array.isArray(value) ? value.map(item => typeof item === 'object' && item ? Object.fromEntries(Object.entries(item).map(([name, child]) => [name, readableActionValue(name, child, run, artifacts)])) : item) : Object.fromEntries(Object.entries(value).map(([name, child]) => [name, readableActionValue(name, child, run, artifacts)])))
  return text(value)
}
function ApprovalReview({ controller, state, run, onClose }) {
  const approval = run.currentApproval, [confirmed, setConfirmed] = useState(false)
  const deadline = Date.parse(approval?.expiresAt), expired = !Number.isFinite(deadline) || deadline <= Date.now()
  const count = approval?.tasks?.length || 0
  const superseded = state.selected?.id === run.id && (state.selected.status !== 'awaiting_approval' || state.selected.currentApproval?.actionDigest !== approval?.actionDigest)
  const decide = decision => controller.perform(async () => { await controller.respondToApproval(run, approval, decision); onClose() })
  return h(ControlDialog, { title: 'Review proposed actions', onClose }, h('div', { className: 'cr-stack' },
    h('p', null, runName(run)), h('p', null, typeof approval?.totalEstimatedCost === 'number' ? `Estimated cost: ${approval.totalEstimatedCost} CLIP` : 'Cost not available'),
    ...(approval?.tasks || []).map((task, index) => h('section', { key: task.id || index, className: 'cr-panel' }, h('h3', null, task.title || task.description || friendly(task.functionName || task.tool || `Action ${index + 1}`)),
      task.description && task.description !== task.title ? h('p', null, task.description) : null,
      task.confirmation?.tool || task.confirmation?.toolName || task.confirmation?.functionName ? h('p', null, `Tool: ${friendly(task.confirmation.tool || task.confirmation.toolName || task.confirmation.functionName)}`) : null,
      ...(approval.presentation?.targets || []).filter(target => target.taskId === task.id).map(target => h('p', { key: `${target.kind}:${target.id}` }, `Target: ${target.label}`)),
      h('dl', null, ...Object.entries(task).filter(([key]) => !['id', 'title', 'description', 'parameters', 'arguments', 'confirmation'].includes(key)).concat(Object.entries(task.parameters || task.arguments || {}), Object.entries(task.confirmation || {}).filter(([key]) => !['planId', 'planSignature', 'tool', 'toolName', 'functionName'].includes(key))).flatMap(([key, value]) => [h('dt', { key: `${key}-label` }, friendly(key)), h('dd', { key }, readableActionValue(key, value, run, state.artifacts))])))),
    h('p', { className: 'cr-muted cr-small' }, `Expires ${dateLabel(approval?.expiresAt)}. Approval applies only to this exact plan. The workflow may request another decision for later actions.`),
    h('label', { className: 'cr-checkbox' }, h('input', { type: 'checkbox', checked: confirmed, disabled: expired || superseded || !actionable(state), onChange: e => setConfirmed(e.target.checked) }), 'I approve these exact targets, settings and estimated cost.'),
    h('div', { className: 'cr-row' }, crButton(`Approve ${count || ''} ${count === 1 ? 'action' : 'actions'}`.replace('  ', ' '), () => decide('approved'), { className: 'cr-button primary', disabled: !confirmed || expired || superseded || !actionable(state) }),
      crButton('Decline plan', () => decide('cancelled'), { disabled: expired || superseded || !actionable(state) })), expired ? h('p', { role: 'alert' }, 'This approval expired. Refresh the workflow for its current plan.') : null,
    superseded ? h('p', { role: 'alert' }, 'The workflow or approval changed. Close this dialog and review the current proposal.') : null,
    state.error ? h('p', { role: 'alert' }, state.error) : null, technical(approval)))
}
function BriefDialog({ controller, state, onClose }) {
  const [goal, setGoal] = useState(''), [kind, setKind] = useState('existing'), [search, setSearch] = useState(''), [source, setSource] = useState(null), [url, setUrl] = useState(''), [file, setFile] = useState(null), [progress, setProgress] = useState(null), [review, setReview] = useState(false)
  const abort = useRef(null), alive = useRef(true), permissions = state.status?.permissions || {}
  useEffect(() => { if (permissions.video_processing || (permissions.clip_generation && state.status?.compatibility?.features?.resourceSearch)) void controller.read(() => controller.loadResources({ kind: permissions.video_processing ? 'video' : 'clip' })); return () => { alive.current = false; abort.current?.abort() } }, [])
  useEffect(() => { if (state.sourceImport?.videoId) setSource({ id: state.sourceImport.videoId, kind: 'video', label: 'Imported video', status: state.sourceImport.status }) }, [state.sourceImport?.videoId])
  const start = () => controller.perform(async () => {
    const result = await controller.mutate('orchestrate', { request: { userMessage: goal.trim(), ...(source ? { [source.kind === 'clip' ? 'clipId' : 'videoId']: source.id } : {}), autoConfirmCostlyTools: false } })
    if (result?.runId) await controller.openRun(result.runId)
    if (result && alive.current) onClose()
  })
  const upload = () => controller.perform(async () => {
    abort.current = new AbortController(); const session = controller.uploadSession()
    const result = await uploadVideo({ call: session.call, save: session.save, receipt: state.uploadReceipt, file, signal: abort.current.signal, onProgress: value => { if (alive.current) setProgress(value) } })
    if (alive.current && result.videoId) { setSource({ id: result.videoId, kind: 'video', label: file.name, status: result.status }); setKind('existing') }
  })
  const sourceRows = state.resourceSearchSupported ? state.resources : state.resources.filter(row => row.label.toLowerCase().includes(search.toLowerCase()))
  return h(ControlDialog, { title: review ? 'Review your brief' : 'New brief', onClose }, h('div', { className: 'cr-stack' },
    review ? h('div', { className: 'cr-stack' }, h('p', null, goal), h('p', null, `Source: ${source?.label || 'No source selected'}`), h('p', { className: 'cr-muted' }, 'Clippy will plan the work. Costly actions require their own exact approval. This starts a real ClipIt workflow.'),
      h('div', { className: 'cr-row' }, crButton('Edit brief', () => setReview(false)), crButton('Start workflow', start, { className: 'cr-button primary', disabled: !actionable(state) || !permissions.clippy_agent }))) : h('div', { className: 'cr-stack' },
      field('What would you like to create?', h('textarea', { value: goal, maxLength: 4000, rows: 4, onChange: e => setGoal(e.target.value), placeholder: 'Find the strongest moments and prepare three short drafts for review.' })),
      h('div', { className: 'cr-row', 'aria-label': 'Brief starting points' }, ...['Find strong moments', 'Prepare short clips', 'Review an existing edit'].map(label => crButton(label, () => setGoal(({ 'Find strong moments': 'Find the strongest moments in this source and explain why they work. Stop for review.', 'Prepare short clips': 'Prepare three short clips from this source. Keep them as drafts and stop for review before paid exports.', 'Review an existing edit': 'Review this source and suggest editing improvements. Stop before making costly changes.' })[label]), { key: label, className: 'cr-button quiet' }))),
      field('Source', h('select', { value: kind, onChange: e => setKind(e.target.value) }, h('option', { value: 'existing' }, 'Existing source'), h('option', { value: 'url', disabled: !permissions.url_extraction }, permissions.url_extraction ? 'Import a URL' : 'URL import requires permission'), h('option', { value: 'file', disabled: !permissions.file_upload }, permissions.file_upload ? 'Upload a video' : 'Upload requires permission'))),
      kind === 'existing' ? h('div', { className: 'cr-stack' }, permissions.video_processing || permissions.clip_generation ? h('div', { className: 'cr-stack' },
        state.status?.compatibility?.features?.resourceSearch ? field('Resource type', h('select', { value: state.resourceQuery.kind || 'video', onChange: e => { setSource(null); void controller.read(() => controller.loadResources({ kind: e.target.value, search })) } }, h('option', { value: 'video', disabled: !permissions.video_processing }, 'Videos'), h('option', { value: 'clip', disabled: !permissions.clip_generation }, 'Clips'))) : null,
        h('form', { onSubmit: e => { e.preventDefault(); void controller.read(() => controller.loadResources({ search, kind: state.resourceQuery.kind || 'video' })) }, className: 'cr-row' }, field(state.resourceSearchSupported ? 'Search sources' : 'Filter loaded sources', h('input', { value: search, onChange: e => setSearch(e.target.value), maxLength: 128 })), crButton('Search sources', undefined, { type: 'submit', disabled: state.loading })),
        field('Choose a named source', h('select', { value: source?.id || '', onChange: e => setSource(state.resources.find(item => item.id === e.target.value) || null) }, h('option', { value: '' }, 'No source selected'), ...sourceRows.map(row => h('option', { key: row.id, value: row.id, disabled: ['failed', 'deleted', 'error', 'processing', 'pending', 'uploading', 'extracting', 'downloading', 'queued'].includes(row.status) }, [row.label, durationLabel(row.durationSeconds), row.status ? friendly(row.status) : null].filter(Boolean).join(' · '))))),
        state.resourcesHasMore ? crButton('Load more sources', () => controller.read(() => controller.loadResources({ ...state.resourceQuery, more: true })), { disabled: state.loading }) : null,
        !state.resourceSearchSupported ? h('p', { className: 'cr-small cr-muted' }, 'This server supports filtering the loaded videos only. Load more to inspect additional sources.') : null) : h('p', { className: 'cr-muted' }, 'This connection cannot read source names. A source-free brief is still available.')) : null,
      kind === 'url' ? h('div', { className: 'cr-stack' }, field('Public video URL', h('input', { type: 'url', value: url, onChange: e => setUrl(e.target.value) })), crButton('Import source', () => controller.perform(async () => { const parsed = new URL(url); if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('Enter a public video URL.'); await controller.mutate('import_url', { url: url.trim() }) }), { disabled: !actionable(state) || !url.trim() }), h('p', { className: 'cr-small cr-muted' }, 'Importing starts a real source job. Check its status before starting the brief.')) : null,
      kind === 'file' ? h('div', { className: 'cr-stack' }, field('Video on this device', h('input', { type: 'file', accept: 'video/*', onChange: e => setFile(e.target.files?.[0] || null) })), state.uploadReceipt ? h('p', null, `Resume file: ${state.uploadReceipt.file.name}`) : null,
        crButton(state.uploadReceipt ? 'Resume upload' : 'Upload video', upload, { disabled: !file || !actionable(state) }), state.busy && abort.current ? crButton('Pause transfer', () => abort.current.abort()) : null, progress != null ? h('progress', { max: 100, value: progress, 'aria-label': 'Video upload progress' }) : null) : null,
      state.uploadReceipt?.intentId ? h('div', { className: 'cr-row' }, crButton('Check upload', () => controller.read(async () => { const receipt = state.uploadReceipt; const result = await controller.call('upload_status', { id: receipt.intentId }); if (alive.current && result.videoId) { setSource({ id: result.videoId, kind: 'video', label: receipt.file.name, status: result.status }); setKind('existing') } }), { disabled: state.loading }), crButton('Abort upload', () => controller.perform(async () => { if (!window.confirm('Abort this upload? The local checkpoint is kept if cancellation fails.')) return; await controller.call('upload_abort', { id: state.uploadReceipt.intentId }); controller.saveUpload(null) }), { disabled: !actionable(state) })) : null,
      state.receipt?.operation === 'import_url' && state.receipt.runId ? crButton('Check imported source', controller.checkImport ? () => controller.read(controller.checkImport) : null, { disabled: state.loading }) : null,
      source ? h('p', null, `Selected: ${source.label}`) : null,
      crButton('Review brief', () => setReview(true), { className: 'cr-button primary', disabled: !goal.trim() || !actionable(state) || !permissions.clippy_agent })),
    state.error ? h('p', { role: 'alert' }, state.error) : null))
}

function ModernReceipt({ controller, state }) {
  const receipt = state.receipt
  if (!receipt || (!receipt.pending && receipt.operation !== 'import_url')) return null
  return h('section', { className: 'cr-banner cr-stack', 'aria-label': 'Operation recovery' },
    h('h3', null, receipt.pending ? 'The last action needs a status check' : 'Source import'),
    h('p', { className: 'cr-muted' }, receipt.pending ? 'The connection did not confirm the result. Check the original operation before starting another action. Do not resubmit it.' : state.sourceImport ? `Import ${friendly(state.sourceImport.status).toLowerCase()}.` : 'The import has a receipt. Check whether the source is ready.'),
    !receipt.corrupt ? h('div', { className: 'cr-row' }, receipt.pending ? crButton('Check original status', () => controller.perform(controller.recover), { disabled: state.busy }) : null,
      receipt.operation === 'import_url' && receipt.runId ? crButton('Check imported source', () => controller.read(controller.checkImport), { disabled: state.loading }) : null) : h('p', null, 'The recovery record is unreadable. Use Classic view diagnostics after inspecting ClipIt.'),
    technical(receipt))
}
function TaskDetail({ controller, state, open, onBack }) {
  const run = state.selected
  if (!run) return h('section', { className: 'cr-detail cr-empty' }, h('h2', null, 'Your work, in view'), h('p', null, 'Select a workflow to see its current phase, decisions and outputs.'))
  const presentation = run.presentation || {}, source = presentation.source
  const outputs = state.artifacts.filter(item => item.presentation?.role === 'output')
  const references = state.artifacts.filter(item => item.presentation?.role !== 'output')
  const approval = run.currentApproval, requested = state.controlRequests[run.id]
  const history = presentation.lineage?.items || []
  return h('article', { className: 'cr-detail', 'aria-label': 'Selected workflow' },
    crButton('Back to activity', onBack, { className: 'cr-button cr-back' }),
    h('header', { className: 'cr-stack' }, h('div', { className: 'cr-row cr-spread' }, badge(runState(run.status), ['awaiting_approval', 'failed'].includes(run.status)),
      crButton('Refresh workflow', () => controller.read(() => controller.loadRun(run.id, true)), { className: 'cr-button quiet', disabled: state.loading })),
      h('h2', { tabIndex: -1 }, runName(run)), source ? h('p', { className: 'cr-muted' }, [source.label, durationLabel(source.durationSeconds)].filter(Boolean).join(' · ')) : h('p', { className: 'cr-muted' }, 'Source details unavailable to this connection'),
      h('p', null, presentation.phase || runState(run.status)), h('p', { className: 'cr-small cr-muted' }, `${presentation.actorLabel || 'ClipIt workflow'} · Updated ${dateLabel(run.updatedAt)}`),
      !run.presentation ? h('p', { className: 'cr-small cr-muted' }, 'This server provides coarse workflow status. Step-level activity may be incomplete.') : null),
    run.detailNeedsRefresh ? h('section', { className: 'cr-panel cr-attention' }, h('h3', null, 'The workflow changed'), h('p', null, 'Refresh its details to review the current decision and controls.')) : null,
    approval && run.status === 'awaiting_approval' ? h('section', { className: 'cr-panel cr-attention' }, h('h3', null, 'Your approval is needed'),
      h('p', null, `${approval.tasks?.length || 'Proposed'} ${approval.tasks?.length === 1 ? 'action is' : 'actions are'} ready to review.`), h('p', { className: 'cr-muted' }, typeof approval.totalEstimatedCost === 'number' ? `Estimated ${approval.totalEstimatedCost} CLIP` : 'Cost not available'),
      h('div', { className: 'cr-row' }, crButton('Review proposed actions', () => open({ type: 'approval', run }), { className: 'cr-button primary', disabled: !actionable(state) }), crButton('Ask for a change', () => open({ type: 'change', run })))) : null,
    run.status === 'failed' ? h('section', { className: 'cr-panel cr-attention' }, h('h3', null, 'This workflow needs help'), h('p', null, presentation.latestActivity?.message || 'Inspect the recorded error and original operation before deciding what to do next.'),
      ...(run.errors || []).map((error, index) => h('p', { key: index }, error.message || error.error || 'The server reported an error.'))) : null,
    requested ? h('p', { role: 'status' }, `${friendly(requested)} requested. Waiting for the server to confirm the change.`) : null,
    h('div', { className: 'cr-row' }, ...(run.allowedControls || []).map(action => crButton(friendly(action), () => open({ type: 'control', run, action }), { key: action, disabled: !actionable(state) || !!requested })),
      !approval ? crButton('Ask for a change', () => open({ type: 'change', run })) : null,
      source?.appUrl ? crButton('Open source in ClipIt', () => appLink(controller, state.status, source.appUrl)) : null),
    h('section', null, h('h3', null, 'Activity'), state.events.length ? h('ol', { className: 'cr-timeline' }, ...state.events.map((event, index) => h('li', { key: event.sequence ?? event.id ?? index }, h('div', null, h('p', null, activityMessage(event)), h('p', { className: 'cr-small cr-muted' }, `${dateLabel(event.occurredAt || event.at)}${event.presentation?.actorLabel ? ` · ${event.presentation.actorLabel}` : ''}`))))) : h('p', { className: 'cr-muted' }, 'No activity entries are available yet.'),
      state.eventsHasMore ? crButton('Load more activity', () => controller.read(controller.moreEvents), { disabled: state.loading }) : null, h('p', { className: 'cr-small cr-muted' }, 'Showing available recorded activity. Older workflows may have partial history.')),
    h('section', null, h('h3', null, 'Outputs'), h(OutputCards, { values: outputs, onReview: item => open({ type: 'output', item }) }), state.artifactsHasMore ? crButton('Load more associated resources', () => controller.read(controller.moreArtifacts), { disabled: state.loading }) : null),
    references.length ? h('section', null, h('h3', null, 'Inputs and references'), h('ul', null, ...references.map(item => h('li', { key: item.id }, `${outputName(item)} · ${friendly(item.presentation?.role || 'unknown association')}`)))) : null,
    history.length ? h('section', null, h('h3', null, 'Related workflow history'), presentation.lineage?.historyLimited ? h('p', { className: 'cr-small cr-muted' }, 'Showing a bounded part of this workflow history.') : null, h('div', { className: 'cr-row' }, ...history.map(item => crButton(`${runName(item)} · ${runState(item.status)}`, () => controller.select(item.id), { key: item.id, disabled: item.id === run.id })))) : null,
    technical({ runId: run.id, status: run.status, lineage: presentation.lineage || run.lineage, progress: run.progress, progressKind: presentation.progressKind || 'unknown' }))
}
function ChangeDialog({ controller, state, run, onClose }) {
  const [request, setRequest] = useState(''), [message, setMessage] = useState(''), draft = changeContext(run, state.artifacts, request)
  const box = useRef(null)
  const copy = async () => {
    controller.saveChangeDraft(draft)
    try {
      if (!window.navigator?.clipboard?.writeText) { box.current?.select(); setMessage('Draft selected. Copy it, then review and send it in your chosen chat.'); return }
      await window.navigator.clipboard.writeText(draft); setMessage('Draft copied. Review and send it in your chosen chat.')
    } catch { box.current?.select(); setMessage('Copy is unavailable. The draft is selected for manual copying.') }
  }
  return h(ControlDialog, { title: 'Ask for a change', onClose }, h('div', { className: 'cr-stack' },
    h('p', { className: 'cr-muted' }, 'Create a context draft for a chat in this Hermes profile. Nothing is sent and the workflow keeps its current state.'),
    field('What would you like changed?', h('textarea', { value: request, maxLength: 4000, onChange: e => setRequest(e.target.value) })),
    field('Review your draft', h('textarea', { value: draft, ref: box, readOnly: true, rows: 8 })),
    h('div', { className: 'cr-row' }, crButton('Copy draft', copy), crButton('Use in composer attachment', () => { controller.saveChangeDraft(draft); setMessage('Draft prepared. In your chosen chat, use Attach → ClipIt workflow context. It is not sent automatically.') })),
    h('p', { role: 'status', 'aria-live': 'polite' }, message)))
}
function AdvancedDialog({ controller, state, onClose, initialTab = 'Connection' }) {
  const [tab, setTab] = useState(initialTab), [doctor, setDoctor] = useState(null)
  const status = state.status, permissions = status?.permissions || {}
  return h(ControlDialog, { title: 'Connection and advanced tools', onClose }, h('div', { className: 'cr-stack' },
    h('nav', { className: 'cr-row', 'aria-label': 'Advanced sections' }, ...['Connection', 'Tools', 'Diagnostics'].map(value => crButton(value, () => { setTab(value); if (value === 'Tools') void controller.read(async () => { await controller.tab('Capabilities') }) }, { key: value, 'aria-pressed': tab === value }))),
    tab === 'Connection' ? h('div', { className: 'cr-stack' }, h('dl', null,
      h('dt', null, 'Account'), h('dd', null, status?.accountLabel || 'ClipIt account'), h('dt', null, 'Workspace'), h('dd', null, status?.scope?.workspaceName || (status?.scope?.enterprise ? 'Workspace name unavailable' : 'Personal workspace')),
      h('dt', null, 'Connection'), h('dd', null, status?.credentialLabel || 'Gateway credential'), h('dt', null, 'Hermes profile'), h('dd', null, host.state.profile.get()), h('dt', null, 'Environment'), h('dd', null, status?.appOrigin || 'Unavailable')),
      h('p', null, 'This view shows work accessible through this connection. It does not list every account agent or Hermes conversation.'),
      h('h3', null, 'Enabled permissions'), h('p', null, Object.entries(permissions).filter(([, enabled]) => enabled).map(([name]) => friendly(name)).join(' · ') || 'No permissions reported'),
      h('p', { className: 'cr-small cr-muted' }, 'Credentials stay in the gateway profile. Rotate or revoke them in ClipIt and update the gateway secret. Removing this plugin does not revoke the shared key.'),
      crButton('Use classic view in this profile', () => { onClose(); void controller.setMode('classic') }), technical(status)) : null,
    tab === 'Tools' ? h(Capabilities, { controller, state }) : null,
    tab === 'Diagnostics' ? h('div', { className: 'cr-stack' }, h('p', null, `Agent Pack ${VERSION} · Contract ${CONTRACT_VERSION}`),
      h('p', null, status?.compatibility?.features?.coordinatedPolling && status?.compatibility?.pollingMode !== 'manual' ? 'Activity refresh uses a shared server budget while this view is open. Hidden views wait at least one minute. Exact approvals and media are refreshed only on request.' : 'This connection uses manual refresh.'),
      crButton('Run Doctor', () => controller.read(async () => setDoctor(await controller.doctor())), { disabled: state.loading }), doctor ? code(doctor) : null) : null))
}
function ModernControlRoom({ controller }) {
  const state = useSyncExternalStore(controller.subscribe, controller.snapshot), profile = useValue(host.state.profile)
  const [dialog, setDialog] = useState(null), [search, setSearch] = useState(''), [outputSearch, setOutputSearch] = useState(''), [announcement, setAnnouncement] = useState('')
  const queue = useRef(null), queueScroll = useRef(0), previousStatus = useRef(null)
  useEffect(() => controller.mount(), [controller])
  useEffect(() => { setDialog(null); setSearch(''); setOutputSearch(''); setAnnouncement(''); previousStatus.current = null }, [profile, state.status?.connectionId, state.status?.credentialId])
  useEffect(() => { const selected = state.selected; if (selected && previousStatus.current?.id === selected.id && previousStatus.current.status !== selected.status) setAnnouncement(`${runName(selected)}: ${runState(selected.status)}.`); previousStatus.current = selected ? { id: selected.id, status: selected.status } : null }, [state.selected?.id, state.selected?.status])
  useEffect(() => {
    if (state.requestedDialog === 'brief') { setDialog({ type: 'brief' }); controller.consumeDialog() }
    else if (state.tab === 'Capabilities' && !dialog) setDialog({ type: 'advanced', tab: 'Tools' })
  }, [state.requestedDialog, state.tab])
  const compatible = state.status?.compatibility?.contractVersion === CONTRACT_VERSION
  const outputs = state.tab === 'Library'
  const workspace = state.status?.scope?.workspaceName || state.status?.accountLabel || 'Your ClipIt workspace'
  const attention = [...new Map([...(state.overview?.runs || []), ...state.runs].map(run => [run.id, run])).values()].filter(run => ['awaiting_approval', 'failed'].includes(run.status))
  const open = value => setDialog(value)
  const choose = id => { queueScroll.current = queue.current?.scrollTop || 0; void controller.select(id) }
  const back = () => { controller.showActivityList(); setTimeout(() => { if (queue.current) { queue.current.scrollTop = queueScroll.current; (queue.current.querySelector('button[aria-current=true]') || queue.current.querySelector('button'))?.focus() } }, 0) }
  const toActivity = () => controller.tab('Runs')
  const toOutputs = () => controller.tab('Library')
  return h('main', { className: 'clipit-control-room', 'aria-label': 'ClipIt Control Room' }, h('style', null, CONTROL_STYLE),
    h('header', { className: 'cr-header' }, h('div', null, h('p', { className: 'cr-small cr-muted' }, 'CLIPIT CONTROL ROOM'), h('h1', null, workspace), h('p', { className: 'cr-small cr-muted' }, 'Work from this connection')),
      h('div', { className: 'cr-row' }, crButton('Connection', () => open({ type: 'advanced' }), { className: 'cr-button quiet' }), crButton('New brief', () => open({ type: 'brief' }), { className: 'cr-button primary', disabled: !actionable(state) || !state.status?.permissions?.clippy_agent }))),
    h('nav', { className: 'cr-nav', 'aria-label': 'ClipIt views' }, crButton('Activity', toActivity, { 'aria-current': !outputs ? 'page' : undefined }), crButton('Outputs', toOutputs, { 'aria-current': outputs ? 'page' : undefined }),
      attention.length ? h('span', { className: 'cr-small cr-muted' }, 'Needs your attention') : null, crButton(state.loading ? 'Refreshing…' : 'Refresh', () => controller.read(controller.refresh), { style: { marginLeft: 'auto' }, disabled: state.loading })),
    h('p', { className: 'cr-sr', role: 'status', 'aria-live': 'polite', 'aria-atomic': true }, announcement),
    state.connectionError ? h('section', { className: 'cr-banner' }, h('h3', null, 'Connection needs attention'), h('p', null, state.connectionError), h('p', { className: 'cr-small cr-muted' }, `Showing the last available data. Last successful update: ${dateLabel(state.lastSuccessAt)}. Actions are paused until the connection refreshes.`)) : null,
    state.overview?.status === 'degraded' ? h('section', { className: 'cr-banner', role: 'status' }, h('h3', null, 'Some information is unavailable'), h('p', null, `Could not refresh ${state.overview.degraded?.map(friendly).join(', ') || 'part of this overview'}. Available workflow data is still shown. Refresh to check again.`)) : null,
    state.error && state.error !== state.connectionError ? h('p', { className: 'cr-banner', role: 'alert' }, state.error) : null,
    !state.connected ? h('section', { className: 'cr-empty' }, h('h2', null, 'Connect your ClipIt workspace'), h('p', null, 'Enable the ClipIt gateway plugin and set its credential with the Hermes secret prompt for this profile.'), crButton('Retry connection', () => controller.read(controller.refresh))) : null,
    state.connected && !compatible ? h('section', { className: 'cr-banner' }, h('h3', null, 'Server update required'), h('p', null, 'This connection does not advertise the Control Room contract. Existing ClipIt clients remain available. Open Connection for details.')) : null,
    h(ModernReceipt, { controller, state }),
    compatible && state.connected && !outputs ? h('div', { className: `cr-split${state.selected && state.showDetail ? ' has-selection' : ''}` },
      h('section', { className: 'cr-queue cr-stack', 'aria-label': 'Activity queue' },
        h('form', { onSubmit: e => { e.preventDefault(); void controller.read(() => controller.loadRuns({ search })) }, className: 'cr-stack' }, field('Search workflows', h('input', { type: 'search', value: search, maxLength: 128, onChange: e => setSearch(e.target.value), placeholder: 'Search by name' })),
          h('div', { className: 'cr-row' }, field('Status', h('select', { value: state.runFilters.status, onChange: e => { const status = e.target.value; void controller.read(() => controller.loadRuns({ status, search })) } },
            ...(state.status?.compatibility?.features?.workflowPresentation ? [['', 'All activity'], ['attention', 'Needs you'], ['in_progress', 'In progress'], ['finished', 'Finished']] : [['', 'All activity'], ['awaiting_approval', 'Needs approval'], ['failed', 'Needs help'], ['active', 'Active'], ['completed', 'Finished']]).map(([value, label]) => h('option', { key: value, value }, label)))), crButton('Search', undefined, { type: 'submit', disabled: state.loading }))),
        attention.some(run => !state.runs.some(row => row.id === run.id)) ? h('div', { className: 'cr-banner' }, h('p', null, 'Other work needs attention.'), crButton('Show attention', () => controller.read(() => controller.loadRuns({ status: state.status?.compatibility?.features?.workflowPresentation ? 'attention' : 'awaiting_approval', search: '' })))) : null,
        state.runs.length ? h('ul', { className: 'cr-list', ref: queue }, ...state.runs.map(run => h('li', { key: run.id }, h('button', { type: 'button', className: 'cr-task', 'aria-current': state.selected?.id === run.id ? 'true' : undefined, onClick: () => choose(run.id) },
          h('strong', null, runName(run)), badge(runState(run.status), ['awaiting_approval', 'failed'].includes(run.status)), run.presentation?.source?.label ? h('span', { className: 'cr-small cr-muted' }, run.presentation.source.label) : null,
          h('span', { className: 'cr-small cr-muted' }, run.presentation?.latestActivity?.message || dateLabel(run.updatedAt)))))) : h('div', { className: 'cr-empty' }, h('h3', null, search || state.runFilters.status ? 'No matching workflows' : 'Your next idea starts here'), h('p', null, search || state.runFilters.status ? 'Adjust your search or filter.' : 'Create a brief to start work, then follow its activity and decisions here.')),
        state.runsHasMore ? crButton('Load more workflows', () => controller.read(() => controller.loadRuns({ more: true })), { disabled: state.loading }) : null),
      h(TaskDetail, { controller, state, open, onBack: back })) : null,
    compatible && state.connected && outputs ? h('section', { className: 'cr-stack', 'aria-label': 'Outputs' }, h('div', null, h('h2', null, 'Outputs'), h('p', { className: 'cr-muted' }, 'Confirmed workflow outputs available through this connection.')),
      h('form', { className: 'cr-row', onSubmit: e => { e.preventDefault(); void controller.read(() => controller.loadLibrary(false, outputSearch, { role: 'output' })) } }, field('Search outputs', h('input', { type: 'search', value: outputSearch, onChange: e => setOutputSearch(e.target.value), maxLength: 128 })),
        field('Readiness', h('select', { value: state.libraryFilters.readiness || '', onChange: e => { void controller.read(() => controller.loadLibrary(false, outputSearch, { role: 'output', readiness: e.target.value })) } }, ...[['', 'All readiness'], ['draft', 'Draft'], ['processing', 'Processing'], ['ready_for_review', 'Ready for review'], ['unavailable', 'Unavailable']].map(([value, label]) => h('option', { key: value, value }, label)))), crButton('Search outputs', undefined, { type: 'submit', disabled: state.loading })),
      h(OutputCards, { values: state.library.filter(item => item.presentation?.role === 'output'), onReview: item => open({ type: 'output', item }) }),
      state.library.some(item => !item.presentation || item.presentation.role === 'unknown') ? h('p', { className: 'cr-muted' }, 'Some older associations have no confirmed output role. Inspect their workflow references in Activity or Classic view.') : null,
      state.libraryHasMore ? crButton('Load more outputs', () => controller.read(() => controller.loadLibrary(true)), { disabled: state.loading }) : null) : null,
    dialog?.type === 'brief' ? h(BriefDialog, { key: `brief:${state.status?.connectionId}`, controller, state, onClose: () => setDialog(null) }) : null,
    dialog?.type === 'approval' ? h(ApprovalReview, { key: dialog.run.currentApproval?.actionDigest, controller, state, run: dialog.run, onClose: () => setDialog(null) }) : null,
    dialog?.type === 'output' ? h(ExactOutput, { key: dialog.item.id, controller, state, item: dialog.item, onClose: () => setDialog(null) }) : null,
    dialog?.type === 'change' ? h(ChangeDialog, { controller, state, run: dialog.run, onClose: () => setDialog(null) }) : null,
    dialog?.type === 'advanced' ? h(AdvancedDialog, { controller, state, initialTab: dialog.tab || 'Connection', onClose: () => { setDialog(null); if (state.tab === 'Capabilities') void toActivity() } }) : null,
    dialog?.type === 'control' ? h(ControlDialog, { title: `${friendly(dialog.action)} workflow`, onClose: () => setDialog(null) }, h('div', { className: 'cr-stack' }, h('p', null, runName(dialog.run)),
      h('p', null, dialog.action === 'retry' ? 'This creates a related attempt only if the server still allows it. Existing paid outputs remain on their original workflow.' : dialog.action === 'cancel' ? 'Request cancellation. Work already completed stays available, and a running operation may take time to stop.' : `Request ${dialog.action}. The status changes only when the server confirms it.`),
      state.error ? h('p', { role: 'alert' }, state.error) : null, crButton(`Request ${dialog.action}`, () => controller.perform(async () => { await controller.control(dialog.run, dialog.action); setDialog(null) }), { className: 'cr-button primary', disabled: !actionable(state) }))) : null)
}
function ControlRoom({ controller }) {
  const state = useSyncExternalStore(controller.subscribe, controller.snapshot)
  return h(state.uiMode === 'classic' ? ClassicControlRoom : ModernControlRoom, { key: `${host.state.profile.get()}:${state.status?.connectionId}:${state.status?.credentialId}`, controller })
}

function Status({ controller }) {
  const state = useSyncExternalStore(controller.subscribe, controller.snapshot)
  const known = [...new Map([...(state.overview?.runs || []), ...state.runs].map(run => [run.id, run])).values()]
  const attention = known.some(run => ['awaiting_approval', 'failed'].includes(run.status))
  const active = known.some(run => !TERMINAL.has(run.status))
  if (!state.error && !attention && !active) return null
  return button(state.error ? state.connectionError ? 'ClipIt: connection needs attention' : 'ClipIt: action needs attention' : `ClipIt: ${attention ? 'work needs attention' : 'work in progress'}`, () => host.navigate('/clipit'))
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
      ...[['open', 'Open ClipIt', 'Overview'], ['start', 'Start a ClipIt run', 'Overview'], ['runs', 'Open ClipIt runs', 'Runs'], ['approvals', 'Review ClipIt approvals', 'Runs'], ['tools', 'Open ClipIt advanced tools', 'Capabilities']].map(([id, label, tab]) => ({
        id, area: PALETTE_AREA, data: { id: `clipit.${id}`, label, keywords: ['clipit', 'clippy', 'video'], run: () => {
          host.navigate('/clipit'); void controller.tab(tab).then(() => id === 'approvals' ? controller.read(() => controller.loadRuns({ status: 'awaiting_approval' })) : id === 'start' && controller.snapshot().uiMode !== 'classic' ? controller.requestBrief() : undefined)
        } }
      })),
      { id: 'activity', area: PANES_AREA, title: 'ClipIt activity', data: { placement: 'right', width: '320px' }, render: () => h(Status, { controller }) },
      { id: 'attach-run', area: COMPOSER_AREAS.attachments, data: { label: 'ClipIt workflow context', icon: 'play-circle', run: target => {
        const run = controller.snapshot().selected
        if (run?.id && /^[a-zA-Z0-9_-]{1,128}$/.test(run.id)) target.insertText(controller.snapshot().changeDraft || changeContext(run, controller.snapshot().artifacts))
        else { host.navigate('/clipit'); void controller.tab('Runs') }
      } } }
    ])
  }
}
