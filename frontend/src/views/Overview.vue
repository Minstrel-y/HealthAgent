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
              <div class="fx-title">指标监测</div>
              <div class="fx-signal-head">
                <div class="fx-num" :style="{ color: abnormalCountColor }">{{ data.abnormal_count }}<span class="fx-unit">项</span></div>
                <div class="fx-sub">异常指标 · {{ !data.scorable_count ? '暂无可自动判读指标' : (data.abnormal_count ? '建议关注' : '已评分指标无异常') }}</div>
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
                <div class="fx-row"><span>BMI 距上次</span>
                  <b :style="{ color: bmiColor }">{{ bmiDeltaText }} <span class="faint">（数值越低越理想）</span></b>
                </div>
              </div>
            </div>

            <div class="fx-card" :class="riskTone">
              <div class="fx-cap">RISK MONITOR <i>03</i></div>
              <div class="fx-title">健康风险提示</div>
              <div class="fx-row" style="margin-bottom:8px;">
                <span>当前评估</span>
                <b><em class="risk" :class="data.report ? data.report.risk_level : 'medium'">{{ riskText }}</em></b>
              </div>
              <p class="fx-text">{{ data.report && data.report.summary ? data.report.summary : '本条记录还没有 AI 解读，点击右侧「生成 AI 解读」可补生成；免费额度限流时约 1 分钟后再试。' }}</p>
              <el-button v-if="!data.report" size="small" type="primary" style="margin-top:10px;"
                         :loading="genLoading" @click="genReport">生成 AI 解读</el-button>
            </div>
          </div>

          <!-- 中：全息人体 -->
          <div class="hero-center">
            <BodyMap2D solo :departments="mapDepartments" />
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

            <div class="fx-card">
              <div class="fx-cap">SYSTEM ANALYSIS <i>05</i></div>
              <div class="fx-title">系统分析 · 关键指标<span class="fx-count">共 {{ metricTotal }} 项</span></div>
              <div class="fx-list">
                <div v-for="it in sysRows" :key="it.key" class="fx-li">
                  <span class="d" :style="{ background: barColor(it.status) }"></span>
                  <span class="n">{{ it.name }}</span>
                  <b :style="{ color: barColor(it.status) }">{{ it.value }}<i class="u">{{ it.unit }}</i></b>
                </div>
              </div>
            </div>

            <div class="fx-card">
              <div class="fx-cap">AI INSIGHT <i>06</i></div>
              <div class="fx-title">智能健康解读</div>
              <p class="fx-text">{{ data.report && data.report.summary ? data.report.summary : '还没有 AI 解读，可先看下方「异常诱因 · 关联疾病分析」（本地规则库即时生成）。' }}</p>
              <ul v-if="aiPoints.length" class="fx-points">
                <li v-for="(a, i) in aiPoints" :key="i">{{ a }}</li>
              </ul>
              <div class="fx-foot muted">AI ASSISTED ANALYSIS · 仅供参考</div>
            </div>
          </div>

          <!-- 系统胶囊：点击跳到对应科室 -->
          <div class="sys-chips">
            <button v-for="d in mergedDepartments" :key="d.name" class="sys-chip"
                    :class="{ alert: d.abnormal }" @click="jumpDept(d.name)">
              {{ shortDept(d.name) }}
              <i v-if="d.abnormal">{{ d.abnormal }}</i>
            </button>
          </div>
        </div>
        </div>

          <div style="margin-top:18px;">
            <InsightPanel :record-id="data.record_id" />
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

const loading = ref(true)
const data = ref({ empty: true })
const genLoading = ref(false)

const RISK_TEXT = { low: '低风险', medium: '中风险', high: '高风险' }
const riskText = computed(() => !data.value.scorable_count ? '缺少可判读指标' : (data.value.report ? (RISK_TEXT[data.value.report?.risk_level] || '需结合报告') : '尚未评估'))

// KPI 卡顶部状态色条
const abnormalTone = computed(() => {
  const n = data.value.abnormal_count || 0
  return n === 0 ? 'ok' : n <= 2 ? 'warn' : 'danger'
})
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

// ---- hero 三栏布局用的派生数据 ----
const allItems = computed(() => (data.value.departments || []).flatMap((d) => d.items))
// 人体光点只接收已有锚点的规则库指标，自定义项目只在详细列表中显示。
const mapDepartments = computed(() => (data.value.departments || [])
  .map(d => ({ ...d, items: d.items.filter(it => it.anchor) }))
  .filter(d => d.items.length))

// 系统分析卡：完全数据驱动——按「偏高 > 临界 > 偏低 > 正常」排序取前 6 条，
// 后端新增任何指标都会自动参与排序并上榜，前端没有硬编码顺序。
const SEV_RANK = { danger: 0, warning: 1, low: 2, normal: 3, none: 4 }
const sysRows = computed(() => [...allItems.value]
  .sort((a, b) => (SEV_RANK[a.status] ?? 4) - (SEV_RANK[b.status] ?? 4))
  .slice(0, 6))
const metricTotal = computed(() => allItems.value.length)

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
  const items = allItems.value.filter(it => it.known)
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
const abnormalCountColor = computed(() => ((data.value.abnormal_count || 0) === 0 ? 'var(--ok)' : (data.value.abnormal_count || 0) <= 2 ? 'var(--warn)' : 'var(--danger)'))

const shortDept = (name) => name.replace(/(内科|科|检验)$/,'')
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
    data.value = await api.overview()
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
</style>
