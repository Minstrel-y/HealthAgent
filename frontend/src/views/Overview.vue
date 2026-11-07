<template>
  <div>
    <div v-if="loading" class="card"><el-skeleton :rows="6" animated /></div>

    <template v-else>
      <div v-if="data.empty" class="card" style="text-align:center;padding:40px;">
        <p class="muted">还没有体检记录，先去「录入体检」提交一次吧</p>
        <el-button type="primary" @click="$router.push('/entry')">去录入体检</el-button>
      </div>

      <template v-else>
        <div class="page-head">
          <div>
            <div class="page-title">最近体检报告</div>
            <div class="muted">体检时间：{{ data.record_time }} · 检查类型：{{ data.check_type_name || '常规体检' }} · 已存入历史档案</div>
          </div>
          <el-button size="small" :loading="loading" @click="load">刷新数据</el-button>
        </div>

        <!-- 第一屏：渐变舞台（同心圆环装饰）+ 左卡片列 / 中央全息人体 / 右卡片列 -->
        <div class="hero-zone">
          <i class="ring r1"></i><i class="ring r2"></i><i class="ring r3"></i>
          <div class="hero3">
          <!-- 左列 -->
          <div class="hero-col col-left">
            <div class="fx-card" :class="scoreTone">
              <div class="fx-cap">HEALTH PROFILE <i>01</i></div>
              <div class="fx-title">个人健康概况</div>
              <div class="fx-big">
                {{ data.score == null ? '—' : data.score }}<span class="fx-unit" v-if="data.score != null">/ 100</span>
              </div>
              <div class="fx-sub">{{ data.score_label }} · {{ data.score == null ? '仅展示未判读项目' : '已收录指标参与评分' }}</div>
              <div class="fx-rows">
                <div class="fx-row"><span>体检时间</span><b>{{ data.record_time }}</b></div>
                <div class="fx-row"><span>风险等级</span>
                  <b><em class="risk" :class="data.report ? data.report.risk_level : 'medium'">{{ riskText }}</em></b>
                </div>
              </div>
            </div>

            <div class="fx-card">
              <div class="fx-cap">HEALTH SIGNAL <i>02</i></div>
              <div class="fx-title">{{ selectedSystem ? `${selectedSystem.label} · 指标监测` : '指标监测' }}</div>
              <div class="fx-signal-head">
                <div class="fx-num" :style="{ color: abnormalCountColor }">{{ currentAbnormal }}<span class="fx-unit">项</span></div>
                <div class="fx-sub">{{ selectedSystem ? selectedSystem.label : '全部已测系统' }} · {{ currentSignalHint }}</div>
              </div>
              <div class="fx-signal">
                <svg viewBox="0 0 240 64" preserveAspectRatio="none" class="sig-svg" aria-hidden="true">
                  <defs>
                    <linearGradient id="hsignal-area" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stop-color="#2dd4bf" stop-opacity="0.42"/>
                      <stop offset="100%" stop-color="#2dd4bf" stop-opacity="0"/>
                    </linearGradient>
                    <linearGradient id="hsignal-stroke" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stop-color="#38bdf8"/>
                      <stop offset="50%" stop-color="#2dd4bf"/>
                      <stop offset="100%" stop-color="#7dd3fc"/>
                    </linearGradient>
                    <filter id="hsignal-glow" x="-20%" y="-60%" width="140%" height="220%">
                      <feGaussianBlur stdDeviation="2.4" result="blur"/>
                      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                    </filter>
                  </defs>
                  <g class="sig-grid" fill="none">
                    <line x1="0" y1="12" x2="240" y2="12"/>
                    <line x1="0" y1="27" x2="240" y2="27"/>
                    <line x1="0" y1="42" x2="240" y2="42"/>
                    <line x1="0" y1="57" x2="240" y2="57"/>
                  </g>
                  <path v-if="signalLinePath" :d="signalAreaPath" class="sig-area" fill="url(#hsignal-area)"/>
                  <path v-if="signalLinePath" :d="signalLinePath" class="sig-line" fill="none" stroke="url(#hsignal-stroke)" filter="url(#hsignal-glow)"/>
                  <g class="sig-dots">
                    <circle v-for="(p, i) in signalPts" :key="i" :cx="p.x" :cy="p.y" :r="dotR(p.status)" :fill="DOT_COLOR[p.status] || '#94a3b8'" :class="p.status"/>
                  </g>
                  <circle v-if="signalPeak" :cx="signalPeak.x" :cy="signalPeak.y" r="3.4" class="sig-peak"/>
                  <circle v-if="signalPeak" :cx="signalPeak.x" :cy="signalPeak.y" r="3.4" class="sig-peak-ring"/>
                </svg>
                <div class="sig-meta">
                  <span>监测点 {{ signalPts.length }}</span>
                  <span v-if="signalPeak" class="sig-peak-label">峰值 · {{ signalPeak.name }}</span>
                </div>
              </div>
              <div class="fx-rows">
                <div class="fx-row" v-if="selectedSystem"><span>本系统检测情况</span>
                  <b>{{ selectedSystem.measured }} 项已录入 · {{ selectedSystem.unrated }} 项未判读</b>
                </div>
                <div class="fx-row" v-else><span>BMI 距上次</span>
                  <b :style="{ color: bmiColor }">{{ bmiDeltaText }} <span class="faint">（仅表示变化，不代表越低越好）</span></b>
                </div>
              </div>
            </div>

            <div class="fx-card" :class="riskTone">
              <div class="fx-cap">RISK MONITOR <i>03</i></div>
              <div class="fx-title">{{ selectedSystem ? `${selectedSystem.label} · 检查提示` : '健康风险提示' }}</div>
              <div class="fx-row" style="margin-bottom:8px;">
                <span>{{ selectedSystem ? '本次相关检测' : '当前评估' }}</span>
                <b v-if="selectedSystem"><em class="tag" :class="selectedSystem.status === 'unrated' ? 'none' : selectedSystem.status">{{ selectedSystemStatus }}</em></b>
                <b v-else><em class="risk" :class="data.report ? data.report.risk_level : 'medium'">{{ riskText }}</em></b>
              </div>
              <p class="fx-text">{{ selectedSystem ? systemRiskMessage : (data.report && data.report.summary ? data.report.summary : '本条记录还没有 AI 解读，可补生成；模型暂不可用时仍能查看本地规则。') }}</p>
              <el-button v-if="!data.report" size="small" type="primary" style="margin-top:10px;"
                         :loading="genLoading" @click="genReport">生成 AI 解读</el-button>
            </div>
          </div>

          <!-- 中：全息人体 -->
          <div class="hero-center">
            <BodyMap2D solo :departments="data.departments || []" :active-group="selectedSystemKey" @select="selectSystem" />
          </div>

          <!-- 右列 -->
          <div class="hero-col col-right">
            <div class="fx-card" :class="scoreTone">
              <div class="fx-cap">STATUS OVERVIEW <i>04</i></div>
              <div class="fx-title">健康状态</div>
              <div class="fx-big">
                {{ data.score == null ? '—' : data.score }}<span class="fx-unit" v-if="data.score != null">/ 100</span>
              </div>
              <div class="fx-bar-track"><i :style="{ width: (data.score ?? 0) + '%' }"></i></div>
              <div class="fx-rows">
                <div class="fx-row"><span>综合风险</span>
                  <b><em class="risk" :class="data.report ? data.report.risk_level : 'medium'">{{ riskText }}</em></b>
                </div>
              </div>
            </div>

            <!-- 右中：人体系统 / 单器官相关指标列表，可进一步点击单项 -->
            <div class="fx-card fx-interact-card">
              <div class="fx-cap">SYSTEM ANALYSIS <i>05</i></div>
              <div class="fx-card-head">
                <div class="fx-title">{{ selectedSystem ? `${selectedSystem.label} · 相关指标` : '选择身体系统' }}
                  <span class="fx-count">{{ selectedSystem ? `${selectedSystem.measured} 项已录入` : `${systemViews.filter(s => s.measured).length} 个系统有数据` }}</span>
                </div>
                <button v-if="selectedSystem" class="fx-text-button" type="button" @click="resetFocus">总览</button>
              </div>
              <p class="fx-interact-hint">{{ selectedSystem ? selectedSystem.hint : '点击人体光点或下方系统名称，逐层查看器官、检验指标与建议。' }}</p>
              <div v-if="!selectedSystem" class="fx-system-grid">
                <button v-for="sys in systemViews" :key="sys.key" class="fx-system-button" type="button"
                        @click="selectSystem(sys)">
                  <span class="d" :style="{ background: barColor(sys.status) }"></span>
                  <span>{{ sys.label }}</span>
                  <b>{{ sys.measured ? `${sys.measured} 项` : '未检测' }}</b>
                </button>
              </div>
              <div v-else-if="!selectedSystem.measured" class="fx-empty-state">
                <b>本次未检测 / 未录入</b>
                <p>没有该系统的相关指标。灰色点位不代表器官健康或异常。</p>
                <el-button size="small" text type="primary" @click="$router.push('/entry')">去录入体检</el-button>
              </div>
              <div v-else class="fx-list fx-metric-list">
                <button v-for="it in currentSystemItems" :key="it.key" type="button" class="fx-li fx-li-button"
                        :class="{ selected: selectedMetricKey === it.key }" :aria-pressed="selectedMetricKey === it.key"
                        @click="selectMetric(it)">
                  <span class="d" :style="{ background: barColor(it.status) }"></span>
                  <span class="n">{{ it.name }}</span>
                  <span class="fx-li-reading"><b :style="{ color: barColor(it.status) }">{{ it.value }}<i class="u">{{ it.unit }}</i></b><small>{{ it.status_label || '未判读' }}</small></span>
                </button>
              </div>
              <p v-if="selectedSystem && selectedSystem.measured" class="fx-interact-foot">点击指标查看参考范围、历史记录与专项建议。</p>
            </div>

            <!-- 右下：全局 → 当前系统 → 当前指标，点击时联动；不重复调用大模型 -->
            <div class="fx-card fx-interact-card fx-advice-card">
              <div class="fx-cap">{{ selectedMetric ? 'METRIC INSIGHT' : selectedSystem ? 'SYSTEM INSIGHT' : 'AI INSIGHT' }} <i>06</i></div>
              <div class="fx-card-head">
                <div class="fx-title">{{ selectedMetric ? `${selectedMetric.name} · 专项解读` : selectedSystem ? `${selectedSystem.label} · 相关解读` : '智能健康解读' }}</div>
                <button v-if="selectedMetric" class="fx-text-button" type="button" @click="selectedMetricKey = null">返回系统</button>
              </div>
              <template v-if="!selectedSystem">
                <p class="fx-text fx-text-more">{{ data.report?.summary || '本次尚无 AI 总结。你可以点击人体部位查看确定性指标和本地规则。' }}</p>
                <ul v-if="aiPoints.length" class="fx-points"><li v-for="(a, i) in aiPoints" :key="i">{{ a }}</li></ul>
              </template>
              <template v-else-if="!selectedSystem.measured">
                <p class="fx-text fx-text-more">本次未录入 {{ selectedSystem.label }} 相关指标，无法判断该系统健康状况。你仍可点击其他灰色点位了解哪些项目尚未检测。</p>
              </template>
              <template v-else-if="selectedMetric">
                <div class="fx-metric-reading">
                  <b :style="{ color: barColor(selectedMetric.status) }">{{ selectedMetric.value }} <small>{{ selectedMetric.unit }}</small></b>
                  <em class="tag" :class="selectedMetric.status === 'none' ? 'none' : selectedMetric.status">{{ selectedMetric.status_label || '未判读' }}</em>
                </div>
                <p class="fx-reference">{{ metricReference }}</p>
                <p class="fx-text fx-text-more">{{ metricDetailSummary }}</p>
                <p v-if="ruleLoading" class="fx-muted-small">专项规则加载中…</p>
                <div v-if="metricHistory.length > 1" class="fx-history">
                  <b>近期数值（相同指标）</b>
                  <span v-for="h in metricHistory" :key="h.id">{{ h.time }}：{{ h.value }}</span>
                </div>
                <div v-if="metricCauses.length" class="fx-advice-section">
                  <b>规则库可能相关因素（非病因诊断）</b>
                  <ul class="fx-points"><li v-for="(cause, i) in metricCauses" :key="i">{{ cause }}</li></ul>
                </div>
                <div v-if="metricAdvice.length" class="fx-advice-section">
                  <b>建议与复查方向</b>
                  <ul class="fx-points"><li v-for="(a, i) in metricAdvice" :key="i">{{ a }}</li></ul>
                </div>
              </template>
              <template v-else>
                <p class="fx-text fx-text-more">{{ systemAnalysisSummary }}</p>
                <div v-if="systemMatchedInsights.length" class="fx-advice-section">
                  <b>本地规则提示</b>
                  <ul class="fx-points"><li v-for="it in systemMatchedInsights.slice(0, 2)" :key="it.key">{{ it.name }}：{{ it.summary }}</li></ul>
                </div>
                <div v-if="systemSuggestions.length" class="fx-advice-section">
                  <b>本地规则建议</b>
                  <ul class="fx-points"><li v-for="(a, i) in systemSuggestions" :key="i">{{ a }}</li></ul>
                </div>
                <p v-else class="fx-muted-small">可点击上方某项指标，查看是否有专项规则和历史数值。</p>
              </template>
              <div class="fx-foot muted">规则及 AI 内容仅供健康科普，不代表器官疾病诊断</div>
            </div>
          </div>

          <!-- 系统快速导航：固定 8 个入口，未测灰色也可以点击。 -->
          <div class="sys-chips">
            <button v-for="sys in systemViews" :key="sys.key" class="sys-chip" type="button"
                    :class="{ alert: sys.abnormal, active: selectedSystemKey === sys.key }"
                    @click="selectSystem(sys)">
              <i class="sys-dot" :style="{ background: barColor(sys.status) }"></i>{{ sys.label }}
              <small>{{ sys.measured ? sys.measured : '—' }}</small>
            </button>
            <button v-if="unmappedItems.length" class="sys-chip" type="button" @click="jumpDept('其他指标')">
              其他未绑定部位的指标 <small>{{ unmappedItems.length }}</small>
            </button>
          </div>
        </div>
        </div>

          <div style="margin-top:18px;">
            <InsightPanel :record-id="data.record_id" :focus-keys="insightFocusKeys" />
          </div>

          <div class="grid-2" style="margin-top:18px;align-items:start;">
            <div id="dept-sec">
              <div class="section-title">分科室评估</div>
              <el-collapse v-model="openDepts" class="dept-collapse">
                <el-collapse-item v-for="d in mergedDepartments" :key="d.name" :name="d.name">
                  <template #title>
                    <span style="font-weight:600;color:var(--ink);">{{ d.name }}</span>
                    <span class="muted" style="margin-left:10px;">{{ d.items.length }} 项</span>
                    <span v-if="d.abnormal" class="tag danger" style="margin-left:8px;">{{ d.abnormal }} 项需关注</span>
                    <span v-else-if="d.items.some(it => it.known)" class="tag normal" style="margin-left:8px;">无已判读异常</span>
                    <span v-else class="tag" style="margin-left:8px;">未判读</span>
                  </template>
                  <div class="metric-row" v-for="it in d.items" :key="it.key">
                    <span>{{ it.name }}<small v-if="it.reference" class="muted" style="display:block;font-weight:normal">参考：{{ it.reference }}（仅供核对）</small></span>
                    <span class="muted">{{ it.value }}<span v-if="it.unit"> {{ it.unit }}</span></span>
                    <span><em class="tag" :class="it.status">{{ it.status_label }}</em></span>
                  </div>
                  <div v-if="d.comment" class="muted" style="margin-top:12px;line-height:1.75;">{{ d.comment }}</div>
                  <ul v-if="d.advice && d.advice.length" style="margin:10px 0 0 18px;padding:0;">
                    <li v-for="(a, i) in d.advice" :key="i" style="line-height:1.8;">{{ a }}</li>
                  </ul>
                </el-collapse-item>
              </el-collapse>
            </div>

            <ChatBox :record-id="data.record_id" height="620px" />
          </div>

        <p class="muted" style="margin-top:16px;">指标状态与评分仅基于已收录的确定性规则；标注「未判读」的项目仅展示原始测量结果。AI 解读仅供健康科普参考，不能替代执业医师诊断。</p>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '@/api'
import BodyMap2D from '@/components/BodyMap2D.vue'
import ChatBox from '@/components/ChatBox.vue'
import InsightPanel from '@/components/InsightPanel.vue'
import { buildSystemViews, systemForItem } from '@/utils/bodySystems'

const loading = ref(true)
const data = ref({ empty: true })
const genLoading = ref(false)

const RISK_TEXT = { low: '低风险', medium: '中风险', high: '高风险' }
const riskText = computed(() => !data.value.scorable_count ? '缺少可判读指标' : (data.value.report ? (RISK_TEXT[data.value.report?.risk_level] || '需结合报告') : '尚未评估'))

// KPI 卡顶部状态色条
const riskTone = computed(() => {
  const r = data.value.report?.risk_level || 'medium'
  return r === 'low' ? 'ok' : r === 'medium' ? 'warn' : 'danger'
})
const scoreTone = computed(() => {
  const s = data.value.score
  if (s === null || s === undefined) return ''
  return s >= 85 ? 'ok' : s >= 70 ? 'warn' : 'danger'
})

const bmiDeltaText = computed(() => {
  const d = data.value.bmi_delta
  if (d === null || d === undefined) return '—'
  return d > 0 ? `+${d}` : String(d)
})
const bmiColor = computed(() => {
  const d = data.value.bmi_delta
  if (d === null || d === undefined) return '#8a8f98'
  return d > 0 ? '#c0392b' : d < 0 ? '#1e7e34' : '#8a8f98'
})

const mergedDepartments = computed(() => {
  const comments = {}
  for (const d of data.value.report?.departments || []) comments[d.name] = d
  return (data.value.departments || []).map((d) => {
    const abnormal = d.items.filter((it) => it.status === 'warning' || it.status === 'danger').length
    return {
      ...d,
      abnormal,
      comment: comments[d.name]?.comment || '',
      advice: comments[d.name]?.advice || []
    }
  })
})

// ---- 点位/指标选择状态：null 为全局，系统点击后进一步点选指标。 ----
const selectedSystemKey = ref(null)
const selectedMetricKey = ref(null)
const allItems = computed(() => (data.value.departments || []).flatMap(d => d.items || []))
const systemViews = computed(() => buildSystemViews(data.value.departments || []))
const selectedSystem = computed(() => systemViews.value.find(s => s.key === selectedSystemKey.value) || null)
const currentSystemItems = computed(() => selectedSystem.value?.items || [])
const selectedMetric = computed(() => currentSystemItems.value.find(i => i.key === selectedMetricKey.value) || null)
const activeSignalItems = computed(() => selectedSystem.value ? currentSystemItems.value : allItems.value)
const unmappedItems = computed(() => allItems.value.filter(i => !systemForItem(i)))
const selectedSystemStatus = computed(() => {
  const s = selectedSystem.value
  if (!s) return ''
  if (!s.measured) return '本次未检测'
  if (s.status === 'unrated') return '仅有未判读数据'
  if (s.abnormal) return `${s.abnormal} 项需关注`
  return s.unrated ? '已判读部分正常；另有未判读' : '已判读项目未见异常'
})
const systemRiskMessage = computed(() => {
  const s = selectedSystem.value
  if (!s?.measured) return '未录入该系统检查项目。没有数据不代表正常，请按实际体检项目评估。'
  if (s.status === 'unrated') return '本次有检测结果，但尚未纳入本地参考规则。请核对原始报告或咨询医生。'
  if (s.abnormal) return `已录入 ${s.measured} 项相关指标，其中 ${s.abnormal} 项出现临界、偏高或偏低。请在右侧选择单项查看规则提示。`
  return `已录入 ${s.measured} 项；已判读部分未见异常。该结果不能代表整个器官或系统完全健康。`
})
const currentAbnormal = computed(() => selectedSystem.value
  ? selectedSystem.value.abnormal
  : allItems.value.filter(i => i.known !== false && ['warning', 'danger', 'low'].includes(i.status)).length)
const currentSignalHint = computed(() => {
  const known = activeSignalItems.value.filter(i => i.known !== false && i.status !== 'none')
  if (!known.length) return '无可判读指标'
  return currentAbnormal.value ? '建议关注' : '已判读部分未见异常'
})
const insightFocusKeys = computed(() => !selectedSystem.value ? null
  : selectedMetric.value ? [selectedMetric.value.key]
    : selectedSystem.value.items.map(i => i.key))
function selectSystem(system) {
  const key = system?.key || system?.keys
  if (!key) return
  selectedSystemKey.value = key
  selectedMetricKey.value = null
}
function resetFocus() {
  selectedSystemKey.value = null
  selectedMetricKey.value = null
}
function selectMetric(item) {
  selectedMetricKey.value = selectedMetricKey.value === item.key ? null : item.key
}

// 直接复用后端一次性生成的报告 + 已存在的本地规则库，不在点击时调用大模型。
const insights = ref({ items: [], cross: [] })
const catalog = ref([])
const historyRecords = ref([])
const ruleRequests = new Map()
const loadedRules = ref({})
let ruleCacheEpoch = 0
const activeRule = ref(null)
const ruleLoading = ref(false)
let ruleRequestVersion = 0
function getLocalRule(key) {
  if (Object.prototype.hasOwnProperty.call(loadedRules.value, key)) return Promise.resolve(loadedRules.value[key])
  if (ruleRequests.has(key)) return ruleRequests.get(key)
  const epoch = ruleCacheEpoch
  const request = api.metricRule(key).then(result => {
    const rule = result && result.title && Array.isArray(result.actions) ? result : null
    if (epoch === ruleCacheEpoch) loadedRules.value = { ...loadedRules.value, [key]: rule }
    return rule
  }).catch(() => null).finally(() => {
    if (ruleRequests.get(key) === request) ruleRequests.delete(key)
  })
  ruleRequests.set(key, request)
  return request
}
const systemMatchedInsights = computed(() => {
  const keys = new Set(currentSystemItems.value.map(i => i.key))
  return (insights.value.items || []).filter(i => keys.has(i.key))
})
const systemAnalysisSummary = computed(() => {
  const s = selectedSystem.value
  if (!s?.measured) return '本次未录入相关检查结果，无法进行该系统的局部分析。'
  if (s.status === 'unrated') return '本次仅有未判读指标，系统不进行自动正常/异常判断。'
  if (systemMatchedInsights.value.length) return `本系统已发现 ${systemMatchedInsights.value.length} 项需关注指标。下列提示来自本地静态规则，供你理解检查结果，并非病因诊断。`
  if (s.unrated) return '已判读的指标未见异常，但仍有未判读项目；建议结合原报告参考范围核对。'
  return '本次已判读的相关指标未见异常。未检查到的项目以及器官结构、功能方面的问题，不能据此排除。'
})
const systemSuggestions = computed(() => {
  // 只使用当前系统异常指标对应的本地专项规则，避免误把跨科室 AI 建议当作器官专属建议。
  const out = []
  for (const metric of systemMatchedInsights.value) {
    const rule = loadedRules.value[metric.key]
    if (!rule) continue
    out.push(...(rule.checks || []).slice(0, 1), ...(rule.actions || []).slice(0, 1))
  }
  return [...new Set(out)].slice(0, 4)
})
const metricHistory = computed(() => {
  const key = selectedMetricKey.value
  if (!key || key.startsWith('custom_')) return []
  return historyRecords.value.filter(r => Number.isFinite(r.metrics?.[key]))
    .slice(-4).map(r => ({ id: r.id, time: (r.record_time || '').slice(0, 10), value: r.metrics[key] }))
})
const metricReference = computed(() => {
  const it = selectedMetric.value
  if (!it) return ''
  if (it.reference) return `本次报告参考范围：${it.reference}`
  if (it.known === false || it.status === 'none') return '未收录本地参考区间，请以原检验报告为准。'
  if (['uric_acid', 'creatinine', 'hgb', 'ggt'].includes(it.key)) return '参考区间与性别等有关，具体以原检验报告为准。'
  const m = catalog.value.find(m => m.key === it.key)
  if (!m || m.high == null) return '请以原检验报告的参考区间为准。'
  return `系统参考范围：${m.low == null ? '≤' + m.high : m.low + '～' + m.high}${m.unit ? ' ' + m.unit : ''}（请以检验机构为准）`
})
const metricDetailSummary = computed(() => {
  const it = selectedMetric.value
  if (!it) return ''
  if (it.known === false || it.status === 'none') return '该项目尚未纳入本地规则库，仅显示原始检查值；不能自动判断是否正常。'
  if (it.status === 'normal') return '本次数值在系统参考范围内。单项数值正常不代表相应器官或系统不存在其他问题。'
  return activeRule.value?.summary || '已发现本地规则标注的异常状态，具体原因需结合症状、参考区间及医生判断。'
})
const metricCauses = computed(() => {
  if (!selectedMetric.value || selectedMetric.value.status === 'normal') return []
  return (activeRule.value?.causes || []).filter(c => c.hit).slice(0, 2).map(c => c.text)
})
const metricAdvice = computed(() => {
  if (!selectedMetric.value || selectedMetric.value.status === 'normal') return []
  const rule = activeRule.value
  return [...(rule?.checks || []).slice(0, 2), ...(rule?.actions || []).slice(0, 2)]
})
// 系统切换时按需获取本系统异常指标的静态规则；请求无额外 AI token 开销。
watch(selectedSystemKey, key => {
  if (!key) return
  for (const item of currentSystemItems.value) {
    if (item.known !== false && ['warning', 'danger', 'low'].includes(item.status)) {
      void getLocalRule(item.key)
    }
  }
})
watch(selectedMetricKey, async key => {
  const version = ++ruleRequestVersion
  activeRule.value = null
  ruleLoading.value = false
  const it = selectedMetric.value
  if (!key || !it || it.known === false || !['warning', 'danger', 'low'].includes(it.status)) return
  ruleLoading.value = true
  try {
    const rule = await getLocalRule(key)
    if (version === ruleRequestVersion) activeRule.value = rule
  } finally {
    if (version === ruleRequestVersion) ruleLoading.value = false
  }
})

// AI 解读卡补充要点（取报告里的科室建议，最多 3 条）
const aiPoints = computed(() => {
  const out = []
  for (const d of data.value.report?.departments || []) {
    for (const a of d.advice || []) {
      if (out.length >= 3) break
      out.push(a)
    }
  }
  return out
})

const STATUS_HEX = { normal: '#059669', warning: '#d97706', danger: '#dc2626', low: '#2563eb', none: '#94a3b8' }
const barColor = (s) => STATUS_HEX[s] || STATUS_HEX.none
// ---- 指标监测 · 健康信号曲线 ----
const STATUS_DEV = { danger: 0.85, warning: 0.55, low: -0.4, normal: 0, none: 0 }

// 相邻点用水平中点做三次贝塞尔控制点 → 平滑且不过冲的曲线
function smoothPath(pts) {
  if (!pts.length) return ''
  if (pts.length === 1) return `M ${pts[0].x} ${pts[0].y}`
  let d = `M ${pts[0].x} ${pts[0].y}`
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i]
    const mx = (a.x + b.x) / 2
    d += ` C ${mx} ${a.y}, ${mx} ${b.y}, ${b.x} ${b.y}`
  }
  return d
}

const signalPts = computed(() => {
  // 未判读的指标没有有效的标准化偏差，不得画进异常信号曲线。
  const items = activeSignalItems.value.filter(it => it.known !== false && it.status !== 'none')
  if (!items.length) return []
  const W = 240, H = 64, padX = 6, padY = 8
  const n = items.length
  return items.map((it, i) => {
    // 后端下发标准化偏差 dev ∈ [-1,1]（0=正常带中点，正=偏高，负=偏低）；
    // 正常项在参考区间内的位置也带来自然起伏，曲线不再拉成一条平线
    const dev = typeof it.dev === 'number'
      ? Math.max(-1, Math.min(1, it.dev))
      : (STATUS_DEV[it.status] ?? 0)
    const x = n === 1 ? W / 2 : padX + (i / (n - 1)) * (W - padX * 2)
    const y = H - padY - ((dev + 1) / 2) * (H - padY * 2)
    return { x: +x.toFixed(1), y: +y.toFixed(1), sev: dev, status: it.status, name: it.name }
  })
})
const signalLinePath = computed(() => smoothPath(signalPts.value))
const signalAreaPath = computed(() => {
  const pts = signalPts.value
  if (!pts.length) return ''
  return `${smoothPath(pts)} L ${pts[pts.length - 1].x} 64 L ${pts[0].x} 64 Z`
})
const DOT_COLOR = { danger: '#ef4444', warning: '#f59e0b', low: '#3b82f6', normal: '#10b981', none: '#94a3b8' }
const dotR = (status) => (status === 'danger' || status === 'warning' ? 3 : 2.1)
const signalPeak = computed(() => {
  if (!signalPts.value.length) return null
  return signalPts.value.reduce((a, b) => (b.sev > a.sev ? b : a))
})
const abnormalCountColor = computed(() => (currentAbnormal.value === 0 ? 'var(--ok)' : currentAbnormal.value <= 2 ? 'var(--warn)' : 'var(--danger)'))

const jumpDept = (name) => {
  if (!openDepts.value.includes(name)) openDepts.value = [...openDepts.value, name]
  document.getElementById('dept-sec')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// 渐进披露：默认展开第一个科室，其余点击再看
const openDepts = ref([])
watch(mergedDepartments, (list) => {
  if (list.length) openDepts.value = [list[0].name]
}, { immediate: true })

const load = async () => {
  loading.value = true
  try {
    const next = await api.overview()
    if (data.value.record_id !== next.record_id) {
      resetFocus()
      // 单指标规则的 hit 由本次记录的数据决定，新记录不能沿用旧记录的缓存。
      ++ruleCacheEpoch
      ++ruleRequestVersion
      loadedRules.value = {}
      activeRule.value = null
      ruleRequests.clear()
    }
    data.value = next
    if (!next.empty) {
      // 次要数据源失败不影响健康总览渲染。
      const results = await Promise.allSettled([
        api.insights(next.record_id), api.metricCatalog(), api.listRecords()
      ])
      if (results[0].status === 'fulfilled') insights.value = results[0].value
      else insights.value = { items: [], cross: [] }
      if (results[1].status === 'fulfilled') catalog.value = results[1].value.metrics || []
      if (results[2].status === 'fulfilled') historyRecords.value = results[2].value || []
    }
  } finally {
    loading.value = false
  }
}

const genReport = async () => {
  genLoading.value = true
  try {
    await api.genReport(data.value.record_id)
    await load()
  } finally {
    genLoading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-top: 4px;
}

/* ---- 第一屏：淡蓝舞台（同心圆环装饰）+ 三栏 ---- */
/* 人体是主图：中间列最宽、并有最小高度；卡片半透明玻璃感、浮在淡蓝底上 */
.hero-zone {
  position: relative;
  margin-top: 20px;
  padding: 30px 36px 22px;
  border-radius: 28px;
  border: 1px solid rgba(255, 255, 255, .55);
  overflow: hidden;
  background:
    radial-gradient(820px 360px at 8% -12%, rgba(255, 255, 255, .35), transparent 58%),
    radial-gradient(760px 380px at 96% 114%, rgba(210, 235, 245, .30), transparent 60%),
    linear-gradient(168deg, rgba(250, 253, 255, .38) 0%, rgba(238, 246, 253, .30) 48%, rgba(232, 241, 251, .38) 100%);
  /* 注意：这里不能加 backdrop-filter —— 会创建隔离的混合组，
     导致人体图的 mix-blend-mode:screen 只能跟这块 38% 透明的背景混合，
     黑色底图会原样透出来变成一个矩形暗块（WebKit/Chromium 行为一致） */
  box-shadow: var(--sh-xs);
}
.hero-zone .ring {
  position: absolute;
  left: 50%;
  top: 46%;
  transform: translate(-50%, -50%);
  border: 1px solid rgba(110, 150, 210, .15);
  border-radius: 50%;
  pointer-events: none;
}
.ring.r1 { width: 340px; height: 340px; }
.ring.r2 { width: 500px; height: 500px; border-color: rgba(110, 150, 210, .10); }
.ring.r3 { width: 680px; height: 680px; border-color: rgba(110, 150, 210, .06); }

.hero3 {
  position: relative;
  display: grid;
  /* 人体居中放大：中间列给最大权重并设最小高度，左右卡片列收窄 */
  grid-template-columns: minmax(0, 0.95fr) minmax(300px, 1.3fr) minmax(0, 1fr);
  gap: 24px;
  align-items: stretch;
}
/* 卡片不撑满整列：按内容高度排布，列内上下撑开（space-between），卡与卡自然留白 */
.hero-col { display: flex; flex-direction: column; justify-content: space-between; gap: 20px; min-width: 0; --fx-shift: 0px; }
.hero-col .fx-card { flex: 0 0 auto; }

/* 两侧信息窗「不规则」排布：四角内收，中间两张略微向外突出；整体再向内收 8px */
.hero-col.col-left .fx-card:first-child,
.hero-col.col-left .fx-card:last-child { --fx-shift: 26px; }
.hero-col.col-left .fx-card:nth-child(2) { --fx-shift: -4px; width: 82%; align-self: flex-start; }
.hero-col.col-right .fx-card:first-child,
.hero-col.col-right .fx-card:last-child { --fx-shift: -26px; }
.hero-col.col-right .fx-card:nth-child(2) { --fx-shift: 4px; width: 82%; align-self: flex-end; }
/* 人体舞台保底高度 → 整行以人体为准拉高，卡片列跟着分布 */
.hero-center { display: flex; min-width: 0; min-height: 640px; padding: 2px 0; }

/* 人体周围的信息窗格：HUD 风格（对齐 HealthAgent1 的 hud-window）——
   半透明蓝玻璃 + 淡蓝描边 + 左上/右下高亮角标，弱化纯白卡片感 */
.fx-card {
  position: relative;
  background: rgba(255, 255, 255, .48);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(79, 150, 191, .29);
  border-radius: 13px;
  padding: 12px 14px;
  box-shadow: 0 12px 30px rgba(65, 126, 166, .075);
  transform: translateX(var(--fx-shift, 0px));
  transition: transform .2s ease, box-shadow .2s ease;
  overflow: hidden;
}
.fx-card:hover { transform: translateX(var(--fx-shift, 0px)) translateY(-2px); box-shadow: 0 14px 30px -8px rgba(65, 126, 166, .22); }

/* 左上 / 右下 高亮角标（HUD 方框特征） */
.fx-card::before,
.fx-card::after {
  content: "";
  position: absolute;
  width: 21px;
  height: 21px;
  pointer-events: none;
}
.fx-card::before {
  top: -1px; left: -1px;
  border-top: 2px solid #73b8df;
  border-left: 2px solid #73b8df;
  border-top-left-radius: 12px;
}
.fx-card::after {
  right: -1px; bottom: -1px;
  border-right: 2px solid #73b8df;
  border-bottom: 2px solid #73b8df;
  border-bottom-right-radius: 12px;
}

/* 顶部状态色条（ok/warn/danger）改用背景渐变，让出 ::after 给右下角标；
   用 color-mix 把色条降到 40% 透明度，弱化突兀感、贴合半透明方框 */
.fx-card.ok {
  background: linear-gradient(color-mix(in srgb, var(--ok) 40%, transparent), color-mix(in srgb, var(--ok) 40%, transparent)) top / 100% 3px no-repeat,
              rgba(255, 255, 255, .48);
}
.fx-card.warn {
  background: linear-gradient(color-mix(in srgb, var(--warn) 40%, transparent), color-mix(in srgb, var(--warn) 40%, transparent)) top / 100% 3px no-repeat,
              rgba(255, 255, 255, .48);
}
.fx-card.danger {
  background: linear-gradient(color-mix(in srgb, var(--danger) 40%, transparent), color-mix(in srgb, var(--danger) 40%, transparent)) top / 100% 3px no-repeat,
              rgba(255, 255, 255, .48);
}

.fx-cap {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 9.5px; font-weight: 700; letter-spacing: 1px; color: var(--faint);
}
.fx-cap i { font-style: normal; opacity: .7; }
.fx-title { font-size: 12.5px; font-weight: 700; color: var(--ink); margin-top: 3px; }
.fx-count {
  margin-left: 8px; font-size: 10px; font-weight: 500; color: var(--faint);
  background: var(--line-soft); border-radius: 999px; padding: 1px 7px;
}

.fx-big { font-size: 29px; font-weight: 700; line-height: 1.1; color: var(--ink); letter-spacing: -.5px; margin-top: 4px; }
.fx-unit { font-size: 11.5px; font-weight: 500; color: var(--sub); margin-left: 3px; letter-spacing: 0; }
.fx-num { font-size: 23px; font-weight: 700; line-height: 1.15; letter-spacing: -.5px; }
.fx-sub { font-size: 11px; color: var(--sub); margin-top: 2px; }

.fx-rows { margin-top: 9px; border-top: 1px solid var(--line-soft); }
.fx-row {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 5.5px 0; font-size: 11.5px; border-bottom: 1px solid var(--line-soft);
}
.fx-row:last-child { border-bottom: none; }
.fx-row span { color: var(--sub); }
.fx-row b { color: var(--ink); font-weight: 600; text-align: right; }

.fx-signal-head { display: flex; align-items: baseline; gap: 10px; margin-top: 6px; }
.fx-signal-head .fx-num { line-height: 1; }
.fx-signal-head .fx-sub { margin-top: 0; }

.fx-signal { position: relative; margin-top: 9px; }
.sig-svg { display: block; width: 100%; height: 62px; overflow: visible; }
.sig-grid line { stroke: rgba(120, 160, 195, .20); stroke-width: 1; vector-effect: non-scaling-stroke; stroke-dasharray: 2 3; }
.sig-line { stroke-width: 2; vector-effect: non-scaling-stroke; stroke-linecap: round; stroke-linejoin: round; }
.sig-dots circle { stroke: rgba(255, 255, 255, .9); stroke-width: .8; }
.sig-peak { fill: #fff; }
.sig-peak-ring {
  fill: none; stroke: #2dd4bf; stroke-width: 1.5;
  transform-box: fill-box; transform-origin: center;
  animation: sig-ring 2.2s ease-out infinite;
}
@keyframes sig-ring {
  0% { transform: scale(0.5); opacity: .95; }
  70% { transform: scale(2.4); opacity: 0; }
  100% { transform: scale(2.4); opacity: 0; }
}
.sig-meta { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 6px; font-size: 10px; color: var(--faint); }
.sig-peak-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.fx-text {
  margin: 6px 0 0; font-size: 11.5px; line-height: 1.65; color: var(--sub);
  display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden;
}
.fx-foot { margin-top: 7px; font-size: 9.5px; letter-spacing: 1px; }
.fx-points { margin: 7px 0 0; padding: 0; list-style: none; }
.fx-points li {
  position: relative; padding-left: 11px; margin-bottom: 3px;
  font-size: 11px; line-height: 1.55; color: var(--sub);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.fx-points li::before {
  content: ""; position: absolute; left: 0; top: 6px;
  width: 5px; height: 5px; border-radius: 50%; background: var(--brand);
}
.fx-bar-track { height: 5px; border-radius: 999px; background: var(--line-soft); margin-top: 8px; overflow: hidden; }
.fx-bar-track i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--brand), var(--accent)); transition: width .4s ease; }

.fx-list { margin-top: 5px; }
.fx-li { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--line-soft); font-size: 11.5px; }
.fx-li:last-child { border-bottom: none; }
.fx-li .d { width: 7px; height: 7px; border-radius: 50%; flex: none; }
.fx-li .n { flex: 1; color: var(--text); }
.fx-li b { font-weight: 700; }
.fx-li .u { font-style: normal; font-size: 10px; font-weight: 400; color: var(--sub); margin-left: 2px; }

/* 系统胶囊 */
.sys-chips {
  position: relative;
  display: flex; flex-wrap: wrap; gap: 11px; justify-content: center;
  margin-top: 20px;
}
.sys-chip {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid rgba(255, 255, 255, .7); background: rgba(255, 255, 255, .62);
  backdrop-filter: blur(10px);
  color: var(--text);
  font: inherit; font-size: 12px; padding: 7px 15px; border-radius: 999px; cursor: pointer;
  box-shadow: 0 2px 8px -3px rgba(40, 70, 120, .14); transition: all .16s ease;
}
.sys-chip:hover { border-color: var(--brand); color: var(--brand); background: var(--brand-soft); transform: translateY(-1px); }
.sys-chip i { font-style: normal; font-size: 11px; font-weight: 700; background: var(--danger); color: #fff; border-radius: 999px; padding: 0 6px; }
.sys-chip.alert { border-color: #f3c1b8; }

.kpi-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }

.dept-collapse {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  overflow: hidden;
  box-shadow: var(--sh-xs);
}
.dept-collapse :deep(.el-collapse-item__header) {
  height: 54px;
  line-height: 54px;
  padding: 0 18px;
  border-bottom: 1px solid var(--line-soft);
  font-size: 14px;
}
.dept-collapse :deep(.el-collapse-item__wrap) { border-bottom: 1px solid var(--line-soft); }
.dept-collapse :deep(.el-collapse-item__content) { padding: 6px 18px 16px; }
.dept-collapse :deep(.el-collapse-item__arrow) { color: var(--faint); }

@media (max-width: 1100px) {
  .hero3 { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  .hero-center { grid-column: 1 / -1; order: -1; max-width: 420px; margin: 0 auto; width: 100%; }
}
@media (max-width: 640px) {
  .hero3 { grid-template-columns: minmax(0, 1fr); }
  .kpi-2 { grid-template-columns: minmax(0, 1fr); }
  .hero-col { --fx-shift: 0px; }
  .hero-col .fx-card { width: 100% !important; }
}

/* ---- 交互式右侧卡：全局 / 系统 / 单指标三级视图 ---- */
.fx-card-head { display: flex; gap: 8px; align-items: center; justify-content: space-between; }
.fx-text-button { flex: none; padding: 3px 7px; font: inherit; font-size: 10.5px; cursor: pointer; color: var(--brand); background: rgba(255,255,255,.8); border: 1px solid #d0e9ec; border-radius: 7px; }
.fx-text-button:hover { background: var(--brand-soft); }
.fx-interact-hint { font-size: 10.5px; line-height: 1.55; color: var(--sub); margin: 5px 0; }
.fx-interact-foot { font-size: 10px; color: var(--faint); margin: 7px 0 0; }
.fx-system-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 3px 8px; margin-top: 6px; max-height: 190px; overflow-y: auto; }
.fx-system-button { display: flex; gap: 5px; align-items: center; padding: 5px 3px; border: 0; border-bottom: 1px solid var(--line-soft); cursor: pointer; background: transparent; font: inherit; font-size: 10px; color: var(--text); text-align: left; }
.fx-system-button:hover { color: var(--brand); background: rgba(239,248,251,.7); }
.fx-system-button .d { width: 7px; height: 7px; border-radius: 50%; flex: none; }
.fx-system-button span:nth-child(2) { flex: 1; }
.fx-system-button b { font-size: 10px; color: var(--faint); white-space: nowrap; }
.fx-metric-list { max-height: 210px; overflow-y: auto; overscroll-behavior: contain; }
.fx-li-button { width: 100%; text-align: left; border: 0; border-bottom: 1px solid var(--line-soft); font: inherit; background: transparent; cursor: pointer; border-radius: 5px; }
.fx-li-button:hover, .fx-li-button.selected { background: rgba(223,242,248,.8); }
.fx-li-button.selected { outline: 1px solid rgba(14,116,144,.3); }
.fx-li-button .n { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fx-li-reading { display: flex; flex-direction: column; align-items: flex-end; flex: none; gap: 0; }
.fx-li-reading small { font-size: 9.5px; color: var(--sub); }
.fx-empty-state { padding: 12px 3px; line-height: 1.6; color: var(--sub); font-size: 11px; }
.fx-empty-state b { display: block; color: var(--text); }
.fx-empty-state p { margin: 4px 0; }
.fx-advice-card { max-height: 340px; overflow-y: auto; overscroll-behavior: contain; }
.fx-text.fx-text-more { display: block; overflow: visible; font-size: 11.5px; }
.fx-metric-reading { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: 8px; }
.fx-metric-reading > b { font-size: 19px; }
.fx-metric-reading small { font-size: 10px; font-weight: 500; }
.fx-reference, .fx-muted-small { font-size: 10.5px; line-height: 1.55; color: var(--sub); margin: 6px 0; }
.fx-history { display: grid; gap: 3px; margin-top: 8px; padding: 7px 9px; background: rgba(245,249,252,.9); border-radius: 8px; font-size: 10.5px; color: var(--text); }
.fx-history b, .fx-advice-section > b { font-size: 11px; color: var(--ink); }
.fx-advice-section { margin-top: 9px; }
.fx-advice-section .fx-points { margin-top: 4px; }
.sys-chip.active { outline: 2px solid rgba(14,116,144,.5); background: var(--brand-soft); }
.sys-chip .sys-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; flex: none; }
.sys-chip small { color: var(--sub); font-size: 10px; }
.fx-card .tag.none { background: #f1f5f9; color: #64748b; }
@media (max-width: 1100px) { .fx-advice-card { max-height: none; } }

</style>
