import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createHash, webcrypto } from 'node:crypto'
import vm from 'node:vm'

const source = await readFile(new URL('../desktop/plugin.js', import.meta.url), 'utf8')
const gib = Number(process.argv[2] || 1)
assert.ok(Number.isInteger(gib) && gib >= 1 && gib <= 10)
const size = gib * 1024 ** 3, partSize = 64 * 1024 ** 2
let largestBuffer = 0, hashedBytes = 0, puts = 0, apiCalls = 0, receipt
const blob = length => ({ size: length,
  slice(start = 0, end = length) { return blob(Math.max(0, Math.min(length, end) - start)) },
  async arrayBuffer() { largestBuffer = Math.max(largestBuffer, length); hashedBytes += length; return new ArrayBuffer(length) }
})
const react = { createElement() {}, useEffect() {}, useRef() {}, useState() {}, useSyncExternalStore() {} }
const sdk = { host: {}, useValue() {}, usePluginI18n() {}, Button() {}, Input() {}, Textarea() {},
  ROUTES_AREA: '', SIDEBAR_NAV_AREA: '', STATUSBAR_AREAS: {}, PALETTE_AREA: '', PANES_AREA: '', COMPOSER_AREAS: {} }
const context = vm.createContext({ URL, TextEncoder, crypto: webcrypto })
const modules = Object.fromEntries(Object.entries({ react, '@hermes/plugin-sdk': sdk }).map(([name, exports]) => [name,
  new vm.SyntheticModule(Object.keys(exports), function () { for (const [key, value] of Object.entries(exports)) this.setExport(key, value) }, { context })]))
const module = new vm.SourceTextModule(source, { context })
await module.link(name => modules[name]); await module.evaluate()
const initialRss = process.memoryUsage().rss, started = performance.now()
await module.namespace.uploadVideo({ file: { ...blob(size), name: 'synthetic-large.mp4', lastModified: 1, type: 'video/mp4' },
  signal: new AbortController().signal, save(value) { receipt = value },
  async call(operation, args) {
    apiCalls++
    if (operation === 'upload_create') return { intentId: 'benchmark-intent', jobId: 'benchmark-job', readyForUpload: true, transport: 'multipart', partCount: size / partSize, partSizeBytes: partSize }
    if (operation === 'upload_status') return { uploadedParts: [] }
    if (operation === 'upload_parts') return { signedPartUrls: [{ partNumber: args.body.partNumbers[0], expectedSizeBytes: partSize, url: 'https://storage.example.test/part?X-Amz-Signature=synthetic' }] }
    if (operation === 'upload_complete') return { status: 'processing' }
    throw new Error(operation)
  },
  async put(url, options) { puts++; assert.equal(options.body.size, partSize); assert.equal(options.credentials, 'omit'); return { ok: true } }
})
assert.ok(largestBuffer <= 8 * 1024 ** 2)
assert.equal(hashedBytes, size * 2)
assert.equal(puts, size / partSize)
assert.ok(!JSON.stringify(receipt).includes('X-Amz'))
console.log(JSON.stringify({ scope: 'Synthetic file geometry and actual hashing; mocked storage/network. Not real-browser or remote transfer acceptance.',
  node: process.version, pluginSha256: createHash('sha256').update(source).digest('hex'), fileBytes: size, partBytes: partSize,
  largestHashBufferBytes: largestBuffer, hashedBytes, putCalls: puts, controlCalls: apiCalls,
  durationMs: performance.now() - started, initialRssBytes: initialRss, peakRssBytes: process.resourceUsage().maxRSS * 1024,
  receiptBytes: Buffer.byteLength(JSON.stringify(receipt)), passed: true }, null, 2))
