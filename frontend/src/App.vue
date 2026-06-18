<template>
  <div class="app">
    <!-- FORM -->
    <div v-if="state === 'form'" class="card">
      <div class="header">
        <h1>CT Assessment System</h1>
        <p class="subtitle">Critical Thinking Evaluation</p>
      </div>

      <div class="field">
        <label>Essay Text</label>
        <textarea
          v-model="essayText"
          rows="12"
          placeholder="Paste your essay here..."
        ></textarea>
      </div>

      <div class="field">
        <label>Language</label>
        <div class="lang-toggle">
          <button :class="{ active: language === 'en' }" @click="language = 'en'">English</button>
          <button :class="{ active: language === 'ru' }" @click="language = 'ru'">Russian</button>
        </div>
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <button class="btn-primary" :disabled="!essayText.trim()" @click="analyze">
        Analyze Essay
      </button>
    </div>

    <!-- LOADING -->
    <div v-else-if="state === 'loading'" class="card card--center">
      <div class="spinner"></div>
      <p class="loading-title">Analyzing...</p>
      <p class="loading-sub">Results in {{ countdown }}s</p>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: progressWidth }"></div>
      </div>
    </div>

    <!-- RESULTS -->
    <div v-else-if="state === 'results'" class="card">
      <div class="header">
        <h2>Analysis Results</h2>
      </div>

      <div class="dimensions">
        <div v-for="dim in dimensions" :key="dim.key" class="dim-row">
          <div class="dim-meta">
            <span class="dim-label">{{ dim.label }}</span>
            <span class="dim-score">{{ score(dim.key) ?? '—' }} / 5</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill" :style="{ width: barWidth(dim.key) }"></div>
          </div>
        </div>
      </div>

      <div class="composite">
        <span class="composite-label">Composite Score</span>
        <span class="composite-val">{{ compositePercent }}%</span>
      </div>

      <div v-if="feedbackText" class="feedback">
        <p class="feedback-label">Feedback</p>
        <p class="feedback-body">{{ feedbackText }}</p>
        <p v-if="weakestDim" class="feedback-focus">
          Focus area: <strong>{{ weakestDim }}</strong>
        </p>
      </div>

      <button class="btn-secondary" @click="reset">Analyze Another Essay</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const API = 'http://127.0.0.1:8000'
const WAIT_SECONDS = 60

const state = ref('form')
const essayText = ref('')
const language = ref('en')
const error = ref('')
const results = ref(null)
const countdown = ref(WAIT_SECONDS)

const dimensions = [
  { key: 'score_arg',         label: 'Argumentation' },
  { key: 'score_evidence',    label: 'Evidence Use' },
  { key: 'score_logic',       label: 'Logical Validity' },
  { key: 'score_perspective', label: 'Multi-Perspectivity' },
  { key: 'score_metacog',     label: 'Metacognitive Reflection' },
]

const progressWidth = computed(
  () => (((WAIT_SECONDS - countdown.value) / WAIT_SECONDS) * 100).toFixed(1) + '%'
)

function score(key) {
  return results.value?.llm_score?.[key] ?? null
}

function barWidth(key) {
  const v = score(key)
  if (v == null) return '0%'
  return ((v / 5) * 100).toFixed(1) + '%'
}

const compositePercent = computed(() => {
  const c = results.value?.llm_score?.score_composite
  return c != null ? Math.round(c * 100) : '—'
})

const feedbackText = computed(() => results.value?.llm_feedback?.feedback_text || '')
const weakestDim  = computed(() => results.value?.llm_feedback?.weakest_dimension || '')

async function analyze() {
  error.value = ''
  state.value = 'loading'
  countdown.value = WAIT_SECONDS

  try {
    const uploadRes = await fetch(`${API}/api/essays/upload/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ essay_text: essayText.value, language: language.value }),
    })
    const uploadData = await uploadRes.json()
    if (!uploadRes.ok) throw new Error(uploadData.error || 'Upload failed')

    const essayId = uploadData.id

    const triggerRes = await fetch(`${API}/api/essays/trigger-scoring/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ essay_id: essayId }),
    })
    if (!triggerRes.ok) {
      const d = await triggerRes.json()
      throw new Error(d.error || 'Scoring trigger failed')
    }

    await new Promise(resolve => {
      const timer = setInterval(() => {
        countdown.value -= 1
        if (countdown.value <= 0) {
          clearInterval(timer)
          resolve()
        }
      }, 1000)
    })

    const resultsRes = await fetch(`${API}/api/essays/${essayId}/results/`)
    const resultsData = await resultsRes.json()
    if (!resultsRes.ok) throw new Error(resultsData.error || 'Failed to fetch results')

    results.value = resultsData
    state.value = 'results'
  } catch (err) {
    error.value = err.message
    state.value = 'form'
  }
}

function reset() {
  essayText.value = ''
  results.value = null
  error.value = ''
  countdown.value = WAIT_SECONDS
  state.value = 'form'
}
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0c0c14; }
</style>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
  color: #dcdce8;
}

/* ── Card ── */
.card {
  background: #14141e;
  border: 1px solid #252535;
  border-radius: 18px;
  padding: 2.5rem;
  width: 100%;
  max-width: 660px;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.5);
}

.card--center {
  text-align: center;
  padding: 3.5rem 2.5rem;
}

/* ── Header ── */
.header { margin-bottom: 2rem; }

h1 {
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: #ffffff;
}

h2 {
  font-size: 1.4rem;
  font-weight: 700;
  color: #ffffff;
}

.subtitle {
  margin-top: 0.3rem;
  font-size: 0.875rem;
  color: #5a5a78;
}

/* ── Form fields ── */
.field { margin-top: 1.5rem; }

label {
  display: block;
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: #5a5a78;
  margin-bottom: 0.5rem;
}

textarea {
  width: 100%;
  background: #0c0c14;
  border: 1px solid #252535;
  border-radius: 10px;
  padding: 0.875rem 1rem;
  color: #dcdce8;
  font-size: 0.925rem;
  line-height: 1.65;
  resize: vertical;
  font-family: inherit;
  transition: border-color 0.18s;
}

textarea::placeholder { color: #3a3a52; }

textarea:focus {
  outline: none;
  border-color: #5757e0;
}

/* ── Language toggle ── */
.lang-toggle {
  display: flex;
  gap: 0.5rem;
}

.lang-toggle button {
  padding: 0.45rem 1.15rem;
  border-radius: 8px;
  border: 1px solid #252535;
  background: transparent;
  color: #5a5a78;
  cursor: pointer;
  font-size: 0.875rem;
  font-family: inherit;
  transition: all 0.18s;
}

.lang-toggle button:hover { color: #9090b8; }

.lang-toggle button.active {
  border-color: #5757e0;
  background: rgba(87, 87, 224, 0.12);
  color: #9090e8;
}

/* ── Buttons ── */
.btn-primary {
  display: block;
  width: 100%;
  margin-top: 2rem;
  padding: 0.875rem;
  background: #5757e0;
  color: #ffffff;
  border: none;
  border-radius: 10px;
  font-size: 0.975rem;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.18s;
}

.btn-primary:hover:not(:disabled) { background: #4444cc; }

.btn-primary:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.btn-secondary {
  display: block;
  width: 100%;
  margin-top: 2rem;
  padding: 0.75rem;
  background: transparent;
  color: #5a5a78;
  border: 1px solid #252535;
  border-radius: 10px;
  font-size: 0.9rem;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.18s;
}

.btn-secondary:hover {
  border-color: #5757e0;
  color: #9090e8;
}

.error {
  margin-top: 0.875rem;
  color: #e05c6a;
  font-size: 0.875rem;
}

/* ── Loading ── */
.spinner {
  width: 48px;
  height: 48px;
  border: 3px solid #252535;
  border-top-color: #5757e0;
  border-radius: 50%;
  animation: spin 0.85s linear infinite;
  margin: 0 auto 1.5rem;
}

@keyframes spin { to { transform: rotate(360deg); } }

.loading-title {
  font-size: 1.1rem;
  font-weight: 500;
  color: #c0c0d4;
}

.loading-sub {
  margin-top: 0.4rem;
  font-size: 0.875rem;
  color: #5a5a78;
}

.progress-track {
  margin-top: 1.75rem;
  height: 3px;
  background: #252535;
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #5757e0;
  border-radius: 999px;
  transition: width 1s linear;
}

/* ── Dimensions ── */
.dimensions {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}

.dim-meta {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.4rem;
}

.dim-label {
  font-size: 0.9rem;
  color: #c0c0d4;
}

.dim-score {
  font-size: 0.8rem;
  color: #5a5a78;
}

.bar-track {
  height: 5px;
  background: #252535;
  border-radius: 999px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #5757e0, #8080ee);
  border-radius: 999px;
  transition: width 0.9s ease;
}

/* ── Composite ── */
.composite {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1.75rem;
  padding: 1rem 1.25rem;
  background: #0c0c14;
  border: 1px solid #252535;
  border-radius: 10px;
}

.composite-label {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: #5a5a78;
}

.composite-val {
  font-size: 1.75rem;
  font-weight: 700;
  color: #8080ee;
  letter-spacing: -0.02em;
}

/* ── Feedback ── */
.feedback {
  margin-top: 1.5rem;
  padding: 1.25rem;
  background: #0c0c14;
  border: 1px solid #252535;
  border-radius: 10px;
}

.feedback-label {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: #5a5a78;
  margin-bottom: 0.625rem;
}

.feedback-body {
  font-size: 0.925rem;
  line-height: 1.7;
  color: #c0c0d4;
}

.feedback-focus {
  margin-top: 0.875rem;
  font-size: 0.825rem;
  color: #5a5a78;
}

.feedback-focus strong { color: #9090e8; }
</style>
