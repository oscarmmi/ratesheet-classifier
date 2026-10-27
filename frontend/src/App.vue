<script setup>
import { computed, ref } from 'vue'

const mappingTypes = ['date', 'tenor', 'currency', 'rate', 'product', 'ignore']
const outputFields = [
  { key: 'product', label: 'Product' },
  { key: 'tenor', label: 'Tenor' },
  { key: 'currency', label: 'Currency' },
  { key: 'rate', label: 'Rate' },
  { key: 'as_of', label: 'As of' },
]

const fileInput = ref(null)
const selectedFile = ref(null)
const sheets = ref([])
const selectedSheetIndex = ref(0)
const loading = ref(false)
const dragActive = ref(false)
const errorMessage = ref('')
const mappingDirty = ref(false)
const overridesBySheet = ref({})

const activeSheet = computed(() => sheets.value[selectedSheetIndex.value] ?? null)
const totalRows = computed(() => sheets.value.reduce((total, sheet) => total + sheet.rows.length, 0))

function chooseFile(file) {
  errorMessage.value = ''
  if (!file) return

  const extension = file.name.split('.').pop()?.toLowerCase()
  if (!['csv', 'xlsx'].includes(extension)) {
    errorMessage.value = 'Choose a CSV or XLSX ratesheet.'
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    errorMessage.value = 'This file is over the 5 MB upload limit.'
    return
  }

  selectedFile.value = file
  sheets.value = []
  mappingDirty.value = false
  overridesBySheet.value = {}
}

function onFileChange(event) {
  chooseFile(event.target.files?.[0])
}

function onDrop(event) {
  dragActive.value = false
  chooseFile(event.dataTransfer.files?.[0])
}

async function runExtraction(mappingOverride = null) {
  if (!selectedFile.value) return

  loading.value = true
  errorMessage.value = ''
  const body = new FormData()
  body.append('file', selectedFile.value)
  if (mappingOverride) body.append('mapping', JSON.stringify({ sheets: mappingOverride }))

  try {
    const response = await fetch('/extract', { method: 'POST', body })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.detail || 'The ratesheet could not be processed.')

    const previousSheet = activeSheet.value?.name
    sheets.value = payload.sheets
    const preservedIndex = sheets.value.findIndex((sheet) => sheet.name === previousSheet)
    selectedSheetIndex.value = preservedIndex >= 0 ? preservedIndex : 0
    mappingDirty.value = false
  } catch (error) {
    errorMessage.value = error instanceof TypeError
      ? 'The API is not reachable. Start FastAPI on port 8000 and try again.'
      : error.message
  } finally {
    loading.value = false
  }
}

function setColumnType(column, type) {
  if (!activeSheet.value) return
  activeSheet.value.mapping = activeSheet.value.mapping.map((item) =>
    item.column === column ? { ...item, type, confidence: 1 } : item,
  )
  overridesBySheet.value = {
    ...overridesBySheet.value,
    [activeSheet.value.name]: Object.fromEntries(activeSheet.value.mapping.map(({ column: name, type: columnType }) => [name, columnType])),
  }
  mappingDirty.value = true
}

function rerunWithCurrentMapping() {
  if (!activeSheet.value) return
  runExtraction(overridesBySheet.value)
}

function formatRate(value) {
  if (value === null || value === undefined) return '—'
  return `${new Intl.NumberFormat('en-US', { maximumFractionDigits: 4 }).format(value)}%`
}

function confidenceLabel(confidence) {
  if (confidence >= 0.8) return 'High'
  if (confidence >= 0.5) return 'Medium'
  return 'Review'
}
</script>

<template>
  <div class="min-h-screen bg-paper text-ink">
    <header class="border-b border-ink/10 bg-white/80">
      <div class="mx-auto flex h-[72px] max-w-[1440px] items-center justify-between px-5 sm:px-8">
        <a class="flex items-center gap-3" href="#workspace" aria-label="Ratesheet Classifier home">
          <span class="grid h-10 w-10 place-items-center rounded-xl bg-ink text-lime" aria-hidden="true">
            <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M5 4.75h9l5 5v9.5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1z" />
              <path d="M14 4.75v5h5M8 14h8M8 17h5" />
            </svg>
          </span>
          <span class="text-sm font-semibold tracking-tight">Ratesheet <span class="text-muted">Classifier</span></span>
        </a>
        <div class="flex items-center gap-2 rounded-full border border-ink/10 bg-paper px-3 py-1.5 text-xs text-muted">
          <span class="h-2 w-2 rounded-full bg-emerald-500"></span>
          Private local processing
        </div>
      </div>
    </header>

    <main id="workspace" class="mx-auto max-w-[1440px] px-5 pb-16 pt-10 sm:px-8 sm:pt-14">
      <div class="mb-9 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p class="mb-3 font-mono text-[10px] uppercase tracking-[0.2em] text-muted">Ratesheet workbench <span class="px-1 text-lime-700">/</span> New analysis</p>
          <h1 class="text-3xl font-semibold tracking-[-0.045em] sm:text-4xl">Make every rate comparable.</h1>
          <p class="mt-3 max-w-2xl text-sm leading-6 text-muted">Upload a CSV or Excel ratesheet. Review the inferred columns, adjust anything that needs a human eye, and extract a normalized table.</p>
        </div>
        <div class="flex gap-2 font-mono text-[10px] uppercase tracking-wider text-muted">
          <span class="rounded-md border border-ink/10 bg-white px-2.5 py-2">CSV</span>
          <span class="rounded-md border border-ink/10 bg-white px-2.5 py-2">XLSX</span>
          <span class="rounded-md border border-ink/10 bg-white px-2.5 py-2">Max 5 MB</span>
        </div>
      </div>

      <div class="grid items-start gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <aside class="space-y-5">
          <section class="rounded-2xl border border-ink/10 bg-white p-5 shadow-panel">
            <div class="mb-4 flex items-center justify-between">
              <h2 class="text-sm font-semibold">Source file</h2>
              <span class="font-mono text-[10px] text-muted">01 / INPUT</span>
            </div>
            <input ref="fileInput" class="sr-only" type="file" accept=".csv,.xlsx" @change="onFileChange" />
            <button
              class="group flex min-h-52 w-full flex-col items-center justify-center rounded-xl border border-dashed px-5 text-center transition"
              :class="dragActive ? 'border-lime-700 bg-lime/20' : 'border-ink/20 bg-paper/70 hover:border-ink/40 hover:bg-paper'"
              type="button"
              @click="fileInput?.click()"
              @dragover.prevent="dragActive = true"
              @dragleave.prevent="dragActive = false"
              @drop.prevent="onDrop"
            >
              <span class="mb-3 grid h-11 w-11 place-items-center rounded-xl bg-white text-ink shadow-sm transition group-hover:-translate-y-0.5" aria-hidden="true">
                <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.7">
                  <path d="M12 15V4m0 0L8 8m4-4 4 4M5 14v5h14v-5" />
                </svg>
              </span>
              <span class="text-sm font-medium">{{ selectedFile ? 'Choose another file' : 'Drop your file here' }}</span>
              <span class="mt-1.5 text-xs text-muted">or browse from your computer</span>
              <span v-if="selectedFile" class="mt-4 max-w-full truncate rounded-md bg-white px-2.5 py-1.5 font-mono text-[10px] text-ink">{{ selectedFile.name }}</span>
            </button>
            <p class="mt-3 text-center text-[11px] text-muted">Your file stays in this local demo session.</p>
            <button
              class="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-ink px-4 py-3 text-sm font-medium text-white transition hover:bg-ink/85 disabled:cursor-not-allowed disabled:opacity-40"
              :disabled="!selectedFile || loading"
              type="button"
              @click="runExtraction()"
            >
              <span v-if="loading" class="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"></span>
              {{ loading ? 'Analyzing ratesheet…' : sheets.length ? 'Analyze again' : 'Analyze ratesheet' }}
              <span v-if="!loading" aria-hidden="true">↗</span>
            </button>
            <div v-if="errorMessage" class="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs leading-5 text-rose-800" role="alert">
              {{ errorMessage }}
            </div>
          </section>

          <section class="rounded-2xl border border-ink/10 bg-ink p-5 text-white">
            <p class="font-mono text-[10px] uppercase tracking-[0.16em] text-lime">What gets extracted</p>
            <div class="mt-4 flex flex-wrap gap-2">
              <span v-for="field in outputFields" :key="field.key" class="rounded-md border border-white/15 bg-white/5 px-2.5 py-1.5 text-[11px] text-white/80">{{ field.label }}</span>
            </div>
            <p class="mt-4 text-xs leading-5 text-white/55">Headers and sample values inform the first pass. You stay in control of the final mapping.</p>
          </section>
        </aside>

        <section class="min-w-0 space-y-5" aria-live="polite">
          <template v-if="sheets.length">
            <div class="grid gap-3 sm:grid-cols-3">
              <article class="rounded-xl border border-ink/10 bg-white p-4 shadow-panel">
                <p class="font-mono text-[10px] uppercase tracking-wider text-muted">Rate records</p>
                <p class="mt-2 text-2xl font-semibold tracking-tight">{{ totalRows }}<span class="ml-2 text-xs font-normal text-muted">rows</span></p>
              </article>
              <article class="rounded-xl border border-ink/10 bg-white p-4 shadow-panel">
                <p class="font-mono text-[10px] uppercase tracking-wider text-muted">Workbook sheets</p>
                <p class="mt-2 text-2xl font-semibold tracking-tight">{{ sheets.length }}<span class="ml-2 text-xs font-normal text-muted">with rates</span></p>
              </article>
              <article class="rounded-xl border border-ink/10 bg-white p-4 shadow-panel">
                <p class="font-mono text-[10px] uppercase tracking-wider text-muted">Current file</p>
                <p class="mt-2 truncate text-sm font-medium" :title="selectedFile?.name">{{ selectedFile?.name }}</p>
              </article>
            </div>

            <section class="overflow-hidden rounded-2xl border border-ink/10 bg-white shadow-panel">
              <div class="flex flex-col justify-between gap-3 border-b border-ink/10 px-5 py-4 sm:flex-row sm:items-center">
                <div>
                  <p class="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">02 / REVIEW</p>
                  <h2 class="mt-1 text-sm font-semibold">Column mapping</h2>
                </div>
                <div v-if="sheets.length > 1" class="flex gap-1 overflow-x-auto rounded-lg bg-paper p-1">
                  <button
                    v-for="(sheet, index) in sheets"
                    :key="sheet.name"
                    class="whitespace-nowrap rounded-md px-3 py-1.5 text-xs transition"
                    :class="selectedSheetIndex === index ? 'bg-white font-medium text-ink shadow-sm' : 'text-muted hover:text-ink'"
                    type="button"
                    @click="selectedSheetIndex = index"
                  >
                    {{ sheet.name }}
                  </button>
                </div>
                <span v-else class="rounded-md bg-paper px-2.5 py-1.5 font-mono text-[10px] text-muted">{{ activeSheet?.name }}</span>
              </div>

              <div class="overflow-x-auto">
                <table class="w-full min-w-[620px] border-collapse text-left">
                  <thead>
                    <tr class="bg-paper/70 font-mono text-[10px] uppercase tracking-wider text-muted">
                      <th class="px-5 py-3 font-medium">Source column</th>
                      <th class="px-5 py-3 font-medium">Detected as</th>
                      <th class="px-5 py-3 font-medium">Confidence</th>
                      <th class="px-5 py-3 font-medium">Sample value</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in activeSheet?.mapping" :key="item.column" class="border-t border-ink/5">
                      <td class="max-w-[180px] truncate px-5 py-3.5 text-xs font-medium" :title="item.column">{{ item.column }}</td>
                      <td class="px-5 py-2.5">
                        <select
                          class="rounded-md border border-ink/10 bg-white px-2.5 py-2 text-xs capitalize outline-none transition focus:border-ink/40 focus:ring-2 focus:ring-lime/60"
                          :value="item.type"
                          :aria-label="`Type for ${item.column}`"
                          @change="setColumnType(item.column, $event.target.value)"
                        >
                          <option v-for="type in mappingTypes" :key="type" :value="type">{{ type }}</option>
                        </select>
                      </td>
                      <td class="px-5 py-3.5">
                        <span class="inline-flex items-center gap-1.5 text-[11px]" :class="item.confidence >= 0.8 ? 'text-emerald-700' : item.confidence >= 0.5 ? 'text-amber-700' : 'text-rose-700'">
                          <span class="h-1.5 w-1.5 rounded-full bg-current"></span>
                          {{ confidenceLabel(item.confidence) }} <span class="font-mono text-muted">{{ Math.round(item.confidence * 100) }}%</span>
                        </span>
                      </td>
                      <td class="max-w-[220px] truncate px-5 py-3.5 font-mono text-[10px] text-muted" :title="item.sample">
                        {{ item.sample || '—' }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div class="flex flex-col justify-between gap-3 border-t border-ink/10 bg-paper/50 px-5 py-3.5 sm:flex-row sm:items-center">
                <p class="text-xs text-muted">{{ mappingDirty ? 'Mapping changed — re-run to update the extracted rows.' : 'Check each detected type before using the extracted table.' }}</p>
                <button
                  class="rounded-lg px-4 py-2.5 text-xs font-medium transition disabled:cursor-not-allowed"
                  :class="mappingDirty ? 'bg-ink text-white hover:bg-ink/85' : 'border border-ink/10 bg-white text-muted'"
                  :disabled="loading || !mappingDirty"
                  type="button"
                  @click="rerunWithCurrentMapping"
                >
                  {{ loading ? 'Re-running…' : 'Re-run extraction' }}
                </button>
              </div>
            </section>

            <section class="overflow-hidden rounded-2xl border border-ink/10 bg-white shadow-panel">
              <div class="flex items-center justify-between border-b border-ink/10 px-5 py-4">
                <div>
                  <p class="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">03 / OUTPUT</p>
                  <h2 class="mt-1 text-sm font-semibold">Normalized rate table</h2>
                </div>
                <span class="rounded-md bg-lime/35 px-2.5 py-1.5 font-mono text-[10px] text-ink">JSON-ready</span>
              </div>
              <div class="overflow-x-auto">
                <table class="w-full min-w-[620px] border-collapse text-left">
                  <thead>
                    <tr class="bg-paper/70 font-mono text-[10px] uppercase tracking-wider text-muted">
                      <th v-for="field in outputFields" :key="field.key" class="px-5 py-3 font-medium">{{ field.label }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, index) in activeSheet?.rows" :key="`${row.product}-${row.tenor}-${index}`" class="border-t border-ink/5">
                      <td class="px-5 py-3.5 text-xs font-medium">{{ row.product ?? '—' }}</td>
                      <td class="px-5 py-3.5 text-xs text-muted">{{ row.tenor ?? '—' }}</td>
                      <td class="px-5 py-3.5 font-mono text-[11px]">{{ row.currency ?? '—' }}</td>
                      <td class="px-5 py-3.5 font-mono text-xs font-medium">{{ formatRate(row.rate) }}</td>
                      <td class="px-5 py-3.5 font-mono text-[11px] text-muted">{{ row.as_of ?? '—' }}</td>
                    </tr>
                    <tr v-if="!activeSheet?.rows.length">
                      <td colspan="5" class="px-5 py-10 text-center text-sm text-muted">No rate rows were found in this sheet.</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="flex items-center justify-between border-t border-ink/10 px-5 py-3 text-[11px] text-muted">
                <span>Normalized fields: product · tenor · currency · rate · as_of</span>
                <span class="font-mono">{{ activeSheet?.rows.length ?? 0 }} rows</span>
              </div>
            </section>
          </template>

          <div v-else class="flex min-h-[540px] flex-col items-center justify-center rounded-2xl border border-dashed border-ink/15 bg-white/55 px-8 text-center">
            <div class="relative mb-8 h-40 w-56">
              <div class="absolute left-8 top-5 h-28 w-32 -rotate-6 rounded-xl border border-ink/10 bg-white shadow-sm"></div>
              <div class="absolute left-16 top-2 h-32 w-32 rotate-3 rounded-xl border border-ink/10 bg-white p-4 shadow-panel">
                <div class="mb-3 h-2 w-12 rounded-full bg-lime"></div>
                <div v-for="line in 4" :key="line" class="mb-2 grid grid-cols-3 gap-2">
                  <span v-for="cell in 3" :key="cell" class="h-3 rounded-sm" :class="line === 1 ? 'bg-ink/10' : 'bg-paper'"></span>
                </div>
              </div>
              <span class="absolute bottom-2 right-3 grid h-10 w-10 place-items-center rounded-xl bg-ink text-lime shadow-lg" aria-hidden="true">↗</span>
            </div>
            <p class="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">Your review space</p>
            <h2 class="mt-2 text-xl font-semibold tracking-tight">A clean table starts with a file.</h2>
            <p class="mt-2 max-w-sm text-sm leading-6 text-muted">Upload a ratesheet to see its inferred columns, review the mapping, and get a normalized result.</p>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>
