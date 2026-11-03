<template>
  <div>
    <div class="page-title">长期指标趋势跟踪</div>
    <p class="muted">健康得分与指标变化全部本地计算，不调用模型；下方三段趋势分析会在首次打开时生成一次。</p>

    <div v-if="loading" class="card"><el-skeleton :rows="8" animated /></div>

    <template v-else-if="points.length">
      <div class="stat-grid">
        <div class="stat">
          <div class="label">当前综合健康得分</div>
          <div class="value">{{ current.score }} <span class="unit">/ 100</span></div>
          <div class="delta muted">{{ scoreLabel }}</div>
        </div>
        <div class="stat">
          <div class="label">距上次变化</div>
          <div class="value" :style="{ color: scoreDeltaColor }">{{ scoreDeltaText }}</div>
        </div>
        <div class="stat">
          <div class="label">记录次数</div>
          <div class="value">{{ points.length }}</div>
        </div>
        <div class="stat">
          <div class="label">最近体检</div>
          <div class="value" style="font-size:20px;">{{ current.record_time }}</div>
        </div>
      </div>

      <div class="card" style="margin-top:16px;">
        <div ref="scoreRef" class="chart"></div>
      </div>

      <div class="grid-2" style="margin-top:16px;align-items:start;">
        <div class="card">
          <div class="card-title">1️⃣ 整体健康趋势总结</div>
          <div v-if="analysisError" class="muted">{{ analysisError }}</div>
          <div v-else-if="!analysis" class="muted">生成中…</div>
          <div v-else style="line-height:1.8;">{{ analysis.trend }}</div>
        </div>
        <div class="card">
          <div class="card-title">2️⃣ 综合影响</div>
          <div v-if="!analysis" class="muted">生成中…</div>
          <div v-else style="line-height:1.8;">{{ analysis.impact }}</div>
        </div>
      </div>

      <div class="card" style="margin-top:16px;">
        <div class="card-title">3️⃣ 具体的运动与作息建议</div>
        <ul v-if="analysis?.advice?.length" style="margin:0 0 0 18px;padding:0;">
          <li v-for="(a, i) in analysis.advice" :key="i" style="line-height:1.9;">{{ a }}</li>
        </ul>
        <div v-else class="muted">暂无建议</div>
      </div>

      <div class="card" style="margin-top:16px;">
        <div class="card-title">各项指标走势</div>
        <div class="grid-2">
          <div v-for="key in seriesKeys" :key="key" style="height:260px;">
            <div :ref="(el) => setChartRef(key, el)" style="width:100%;height:260px;"></div>
          </div>
        </div>
        <div v-if="!seriesKeys.length" class="muted">暂无可用于绘制趋势的结构化指标</div>
      </div>

      <p class="muted" style="margin-top:12px;">本结果由 AI 生成，仅为健康科普参考，不能替代执业医师诊断。</p>
    </template>

    <div v-else class="card" style="text-align:center;padding:40px;">
      <p class="muted">暂无体检记录，请先录入体检数据</p>
      <el-button type="primary" @click="$router.push('/entry')">去录入体检</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { api } from '@/api'

const loading = ref(true)
const points = ref([])
const series = ref({})
const analysis = ref(null)
const analysisError = ref('')

const scoreRef = ref(null)
const chartRefs = {}
let scoreChart = null
const metricCharts = {}

// 标签也来自后端指标库：新增指标在趋势图上会显示中文名而不是原始 key
const METRIC_LABEL = ref({
  bmi: 'BMI', sbp: '收缩压 mmHg', dbp: '舒张压 mmHg',
  fast_glucose: '空腹血糖 mmol/L', tg: '甘油三酯 mmol/L', non_hdl: '非高密度脂蛋白 mmol/L',
  alt: 'ALT U/L', uric_acid: '尿酸 μmol/L', creatinine: '肌酐 μmol/L'
})

const current = computed(() => points.value[points.value.length - 1] || { score: 0, record_time: '—' })
const prev = computed(() => points.value[points.value.length - 2] || null)
const seriesKeys = computed(() => Object.keys(series.value))

const scoreLabel = computed(() => {
  const s = current.value.score
  if (s >= 90) return '优秀'
  if (s >= 80) return '良好'
  if (s >= 70) return '一般'
  if (s >= 60) return '偏差'
  return '较差'
})
const scoreDeltaText = computed(() => {
  if (!prev.value) return '—'
  const d = current.value.score - prev.value.score
  return d > 0 ? `+${d} 分` : `${d} 分`
})
const scoreDeltaColor = computed(() => {
  if (!prev.value) return '#8a8f98'
  const d = current.value.score - prev.value.score
  return d > 0 ? '#1e7e34' : d < 0 ? '#c0392b' : '#8a8f98'
})

const setChartRef = (key, el) => {
  if (el) chartRefs[key] = el
}

const drawScore = () => {
  if (!scoreRef.value) return
  scoreChart = echarts.init(scoreRef.value)
  scoreChart.setOption({
    title: { text: '综合健康得分趋势（满分 100）', textStyle: { fontSize: 15, fontWeight: 600, color: '#0f172a' } },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,.96)',
      borderColor: '#e6ebf1',
      textStyle: { color: '#1e293b', fontSize: 13 }
    },
    grid: { left: 46, right: 24, top: 56, bottom: 34 },
    xAxis: {
      type: 'category',
      data: points.value.map((p) => p.record_time),
      axisLine: { lineStyle: { color: '#e6ebf1' } },
      axisLabel: { color: '#64748b' },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 108,
      axisLine: { show: false },
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { color: '#f0f4f8' } }
    },
    series: [{
      type: 'line',
      data: points.value.map((p) => p.score),
      smooth: true,
      symbolSize: 9,
      label: { show: true, position: 'top', color: '#0e7490', fontWeight: 600 },
      lineStyle: { color: '#0e7490', width: 3, shadowBlur: 8, shadowColor: 'rgba(14,116,144,.35)' },
      itemStyle: { color: '#0e7490', borderColor: '#fff', borderWidth: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(45,212,191,.34)' },
          { offset: 1, color: 'rgba(45,212,191,0)' }
        ])
      },
      markLine: {
        silent: true,
        symbol: 'none',
        label: { fontSize: 11, color: '#64748b' },
        data: [
          { yAxis: 90, lineStyle: { color: '#059669', type: 'dashed' }, label: { formatter: '优秀 90' } },
          { yAxis: 70, lineStyle: { color: '#b45309', type: 'dashed' }, label: { formatter: '及格 70' } }
        ]
      }
    }]
  })
}

const drawMetrics = () => {
  for (const key of seriesKeys.value) {
    const el = chartRefs[key]
    if (!el) continue
    const chart = echarts.init(el)
    chart.setOption({
      title: { text: METRIC_LABEL.value[key] || key, textStyle: { fontSize: 13, fontWeight: 600, color: '#0f172a' } },
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,.96)', borderColor: '#e6ebf1' },
      grid: { left: 48, right: 18, top: 42, bottom: 28 },
      xAxis: {
        type: 'category',
        data: series.value[key].map((p) => p.t),
        axisLine: { lineStyle: { color: '#e6ebf1' } },
        axisLabel: { color: '#64748b' },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        scale: true,
        axisLine: { show: false },
        axisLabel: { color: '#64748b' },
        splitLine: { lineStyle: { color: '#f0f4f8' } }
      },
      series: [{
        type: 'line',
        data: series.value[key].map((p) => p.v),
        smooth: true,
        symbolSize: 7,
        itemStyle: { color: '#14b8a6', borderColor: '#fff', borderWidth: 2 },
        lineStyle: { color: '#14b8a6', width: 2 }
      }]
    })
    metricCharts[key] = chart
  }
}

const loadAnalysis = async () => {
  try {
    const res = await api.trendAnalysis()
    analysis.value = res.data
  } catch (e) {
    analysisError.value = '三段趋势分析暂不可用（通常是免费额度限流），可在问答页直接提问。'
  }
}

onMounted(async () => {
  // 指标中文名（失败时用上面的默认表兜底）
  try {
    const res = await api.metricCatalog()
    for (const m of res?.metrics || []) {
      METRIC_LABEL.value[m.key] = m.unit ? `${m.name} ${m.unit}` : m.name
    }
  } catch { /* 忽略 */ }
  try {
    const res = await api.trend()
    points.value = res.points || []
    series.value = res.series || {}
  } finally {
    loading.value = false
  }
  if (!points.value.length) return
  await nextTick()
  drawScore()
  drawMetrics()
  loadAnalysis()
  window.addEventListener('resize', () => {
    scoreChart?.resize()
    Object.values(metricCharts).forEach((c) => c.resize())
  })
})
</script>
