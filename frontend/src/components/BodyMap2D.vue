<template>
  <div class="bodymap-wrap" :class="{ solo }">
    <div class="bodymap-inner" :class="{ solo }">
      <!-- 中：深色全息人体舞台 -->
      <div class="body-stage">
        <img class="body-img" src="/models/body_render.png" alt="人体全息图" draggable="false" />
        <div v-for="m in markers" :key="m.keys" class="marker"
             :class="{ pulse: m.status === 'warning' || m.status === 'danger', active: selected && selected.keys === m.keys }"
             :style="{ left: m.x + '%', top: m.y + '%' }"
             @click="$emit('select', m); selected = m">
          <span class="halo" :style="{ background: colorOf(m.status) }"></span>
          <span class="ring"></span>
          <span class="core" :style="{ background: colorOf(m.status), boxShadow: '0 0 10px ' + colorOf(m.status) }"></span>
        </div>
      </div>

      <!-- 右：指标小卡片网格（独立布局模式下隐藏，由父组件放两侧） -->
      <div v-if="!solo" class="metric-grid">
        <div v-for="m in markers" :key="m.keys" class="metric-card"
             :class="{ active: selected && selected.keys === m.keys }"
             @click="$emit('select', m); selected = m">
          <div class="m-head">
            <em class="dot" :style="{ background: colorOf(m.status) }"></em>
            <span class="m-name">{{ shortName(m.label) }}</span>
          </div>
          <div class="m-value" :style="{ color: colorOf(m.status) }">{{ m.display }}</div>
          <div class="m-foot">
            <span class="m-organ">{{ organOf(m.label) }}</span>
            <span class="m-status" :style="{ color: colorOf(m.status), background: colorOf(m.status) + '1a' }">{{ statusText(m.status) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 未标注身体部位的指标（新增项目等）：以标签形式补齐展示 -->
    <div v-if="unmapped.length" class="unmapped">
      <span class="um-cap">未在图上标注</span>
      <span v-for="it in unmapped" :key="it.key" class="um-chip">
        <em class="dot" :style="{ background: colorOf(it.status) }"></em>
        {{ it.name }}
        <b :style="{ color: colorOf(it.status) }">{{ it.value }}<i v-if="it.unit">{{ it.unit }}</i></b>
        <em class="um-st">{{ it.status_label }}</em>
      </span>
    </div>

    <!-- 选中详情 -->
    <transition name="fade">
      <div v-if="selected" class="metric-detail">
        <b>{{ selected.label }}</b>
        <p>{{ selected.text }}</p>
      </div>
    </transition>

    <div class="legend">
      <span><em class="dot" style="background:#1e7e34;"></em>正常</span>
      <span><em class="dot" style="background:#e67e22;"></em>临界</span>
      <span><em class="dot" style="background:#c0392b;"></em>偏高</span>
      <span><em class="dot" style="background:#9aa7b5;"></em>无数据</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  departments: { type: Array, default: () => [] },
  solo: { type: Boolean, default: false } // true = 只渲染人体舞台，卡片由父组件布局在两侧
})
defineEmits(['select'])

const selected = ref(null)

const STATUS_COLOR = { normal: '#1e7e34', warning: '#e67e22', danger: '#c0392b', low: '#3a8ee6', none: '#9aa7b5' }
const STATUS_TEXT = { normal: '正常', warning: '临界', danger: '偏高', low: '偏低', none: '无数据' }
const colorOf = (s) => STATUS_COLOR[s] || STATUS_COLOR.none
const statusText = (s) => STATUS_TEXT[s] || '无数据'
const shortName = (label) => label.split(' · ')[0]
const organOf = (label) => label.split(' · ')[1] || ''

// 身体光点完全由后端返回的 anchor（部位坐标）生成：
// 新增体检项目只要在后端指标库登记了锚点，人体图上就会自动出现光点，前端不用改代码。
const rank = { none: 0, low: 1, normal: 2, warning: 3, danger: 4 }

const markers = computed(() => {
  const map = new Map()
  for (const g of props.departments) {
    for (const it of g.items || []) {
      const a = it.anchor
      if (!a) continue
      const key = a.group || `${a.x},${a.y}`
      if (!map.has(key)) {
        map.set(key, { keys: key, x: a.x, y: a.y, organ: a.organ, names: [], texts: [], values: [], status: 'none' })
      }
      const m = map.get(key)
      if ((rank[it.status] ?? 0) > rank[m.status]) m.status = it.status
      m.names.push(it.name)
      m.values.push(`${it.value}${it.unit ? it.unit : ''}`)
      m.texts.push(`${it.name} ${it.value}${it.unit ? ' ' + it.unit : ''}（${it.status_label}）`)
    }
  }
  return [...map.values()].map((m) => ({
    ...m,
    label: `${m.names.slice(0, 2).join('、')} · ${m.organ}`,
    display: m.values.length ? m.values.slice(0, 2).join(' / ') : '—',
    text: m.texts.length ? m.texts.join('；') : '本次未检测该项目'
  }))
})

// 没有身体部位锚点的指标（新加入但还没标位置的项目），以标签形式列在人体下方，不丢数据
const unmapped = computed(() => {
  const out = []
  for (const g of props.departments) {
    for (const it of g.items || []) if (!it.anchor) out.push(it)
  }
  return out
})

watch(() => props.departments, () => { selected.value = null })
</script>

<style scoped>
.bodymap-wrap { position: relative; width: 100%; }
.bodymap-wrap.solo { height: 100%; display: flex; flex-direction: column; }

.bodymap-inner {
  display: flex;
  gap: 16px;
  align-items: stretch;
  flex: 1;
  min-height: 0;
}
/* solo 模式：舞台随行高伸缩，人体完整显示（contain）；详情与图例显示在人体下方 */
.bodymap-inner.solo { display: block; }
.bodymap-inner.solo .body-stage { width: 100%; height: 100%; min-height: 0; }
.bodymap-inner.solo .body-img { height: 100%; object-fit: contain; }

/* 左：全息人体 + 柔和深蓝光晕垫底（边缘渐隐融进浅色页面，没有硬边盒子） */
.body-stage {
  position: relative;
  flex: 1;
  min-width: 0;
}
.body-stage::before {
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 150%;
  height: 112%;
  border-radius: 50%;
  background: radial-gradient(closest-side,
    rgba(15, 36, 72, .92) 0%,
    rgba(15, 36, 72, .62) 55%,
    rgba(15, 36, 72, .22) 80%,
    rgba(15, 36, 72, 0) 100%);
}
.body-img {
  position: relative;
  z-index: 1;
  display: block;
  width: 100%;
  height: auto;
  user-select: none;
  mix-blend-mode: screen;
  filter: saturate(1.3);
}

/* 白底光点（深底上更醒目，带辉光） */
.marker { position: absolute; width: 0; height: 0; cursor: pointer; z-index: 2; }
.marker .ring {
  position: absolute;
  left: -9px;
  top: -9px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 2px 6px rgba(31, 58, 104, 0.28);
  transition: transform 0.15s ease;
}
.marker .core {
  position: absolute;
  left: -4px;
  top: -4px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transition: transform 0.15s ease;
}
.marker:hover .ring, .marker.active .ring { transform: scale(1.35); }
.marker .halo {
  position: absolute;
  left: -12px;
  top: -12px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  opacity: 0;
}
.marker.pulse .halo { opacity: 0.35; animation: pulse 1.6s ease-out infinite; }
@keyframes pulse {
  0% { transform: scale(0.6); opacity: 0.45; }
  70% { transform: scale(1.7); opacity: 0; }
  100% { transform: scale(1.7); opacity: 0; }
}

/* 右：指标小卡片 */
.metric-grid {
  flex: 1.05;
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
  align-content: center;
}
.metric-card {
  min-width: 0;
  background: #fff;
  border: 1px solid #e7edf7;
  border-radius: 12px;
  padding: 9px 11px;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(31, 58, 104, 0.06);
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.metric-card:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(31, 58, 104, 0.12); }
.metric-card.active { border-color: #7fa8e0; box-shadow: 0 8px 20px rgba(31, 58, 104, 0.16); }

.m-head { display: flex; align-items: center; gap: 6px; min-width: 0; }
.m-head .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; flex: none; }
.m-name { font-size: 12px; color: #7a8aa0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.m-value {
  margin-top: 4px;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.m-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 4px; }
.m-organ { font-size: 11px; color: #9aa7b8; }
.m-status { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 999px; }

/* 未标注部位的项目 */
.unmapped {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
  margin-top: 10px; padding: 8px 10px;
  background: #fff; border: 1px dashed #d9e2ef; border-radius: 12px;
}
.um-cap { font-size: 11px; color: #9aa7b8; margin-right: 2px; }
.um-chip {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11.5px; color: #5a6b7d;
  background: #f5f8fc; border-radius: 999px; padding: 3px 9px;
}
.um-chip .dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; flex: none; }
.um-chip b { font-weight: 700; }
.um-chip i { font-style: normal; font-size: 10px; font-weight: 400; color: #9aa7b8; }
.um-st { font-style: normal; font-size: 10.5px; color: #9aa7b8; }

/* 详情条 */
.metric-detail {
  margin-top: 12px;
  background: #fff;
  border: 1px solid #e7edf7;
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 13px;
  line-height: 1.7;
  box-shadow: 0 4px 14px rgba(31, 58, 104, 0.06);
}
.metric-detail b { color: #0f4c81; }
.metric-detail p { margin: 4px 0 0; color: #5a6b7d; }

.legend {
  display: flex;
  justify-content: center;
  gap: 12px;
  font-size: 11.5px;
  color: #6b7280;
  margin-top: 10px;
}
.legend .dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 4px; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (max-width: 640px) {
  .bodymap-inner { flex-direction: column; }
}
</style>
