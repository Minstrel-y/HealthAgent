<template>
  <div class="bodymap-wrap" :class="{ solo }">
    <div class="bodymap-inner" :class="{ solo }">
      <!-- 原版全息人体舞台：背景渐变、图片混合模式、位置与尺寸都保留。 -->
      <div ref="stage" class="body-stage">
        <img ref="bodyImage" class="body-img" src="/models/body_render.png" alt="人体全息图"
             draggable="false" @load="fitImage" @error="imageError = true" />

        <!-- 只叠加透明点位层。点位与 contain 后实际显示的图片对齐，不改变图片或背景。 -->
        <div v-if="artRect.width && artRect.height" class="marker-layer" :style="artStyle">
          <button v-for="system in systemViews" :key="system.key" type="button" class="marker"
                  :class="{ pulse: system.status === 'warning' || system.status === 'danger', active: activeGroup === system.key }"
                  :style="{ left: system.x + '%', top: system.y + '%', '--marker-color': colorOf(system.status) }"
                  :aria-pressed="activeGroup === system.key"
                  :aria-label="`${system.label}，${statusText(system.status)}，${system.measured} 项相关指标`"
                  :title="`${system.label} · ${statusText(system.status)} · ${system.hint}`"
                  @click="selectSystem(system)">
            <span class="halo"></span>
            <span class="ring"></span>
            <span class="core"></span>
          </button>
        </div>
        <span v-if="imageError" class="body-image-error">找不到 /models/body_render.png，请检查原人体图片</span>
      </div>

      <!-- 非 solo 模式沿用原版双列白色指标卡样式，仅把内容改成系统导航。 -->
      <div v-if="!solo" class="metric-grid">
        <button v-for="system in systemViews" :key="system.key" type="button" class="metric-card"
                :class="{ active: activeGroup === system.key }" @click="selectSystem(system)">
          <div class="m-head">
            <em class="dot" :style="{ background: colorOf(system.status) }"></em>
            <span class="m-name">{{ system.label }}</span>
          </div>
          <div class="m-value" :style="{ color: colorOf(system.status) }">
            {{ system.measured ? `${system.measured} 项已录入` : '—' }}
          </div>
          <div class="m-foot">
            <span class="m-organ">{{ system.area }}</span>
            <span class="m-status" :style="{ color: colorOf(system.status), background: colorOf(system.status) + '1a' }">
              {{ statusText(system.status) }}
            </span>
          </div>
        </button>
      </div>
    </div>

    <div v-if="unmapped.length && !solo" class="unmapped">
      <span class="um-cap">未在图上标注</span>
      <span v-for="it in unmapped" :key="it.key" class="um-chip">
        <em class="dot" :style="{ background: colorOf(it.status) }"></em>
        {{ it.name }}
        <b :style="{ color: colorOf(it.status) }">{{ it.value }}<i v-if="it.unit">{{ it.unit }}</i></b>
        <em class="um-st">{{ it.status_label || '未判读' }}</em>
      </span>
    </div>

    <div class="legend">
      <span><em class="dot" style="background:#1e7e34;"></em>正常</span>
      <span><em class="dot" style="background:#e67e22;"></em>临界</span>
      <span><em class="dot" style="background:#c0392b;"></em>偏高</span>
      <span><em class="dot" style="background:#3a8ee6;"></em>偏低</span>
      <span><em class="dot" style="background:#9aa7b5;"></em>未检测</span>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { buildSystemViews, systemForItem, STATUS_TEXT } from '@/utils/bodySystems'

const props = defineProps({
  departments: { type: Array, default: () => [] },
  solo: { type: Boolean, default: false },
  activeGroup: { type: String, default: null }
})
const emit = defineEmits(['select'])
const systemViews = computed(() => buildSystemViews(props.departments))
const colorOf = status => ({
  normal: '#1e7e34', warning: '#e67e22', danger: '#c0392b',
  low: '#3a8ee6', none: '#9aa7b5', unrated: '#9aa7b5'
}[status] || '#9aa7b5')
const statusText = status => STATUS_TEXT[status] || '未检测'
const selectSystem = system => emit('select', system)
const unmapped = computed(() => (props.departments || []).flatMap(d => d.items || []).filter(it => !systemForItem(it)))

const stage = ref(null)
const bodyImage = ref(null)
const imageError = ref(false)
const artRect = ref({ left: 0, top: 0, width: 0, height: 0 })
const artStyle = computed(() => ({
  left: `${artRect.value.left}px`,
  top: `${artRect.value.top}px`,
  width: `${artRect.value.width}px`,
  height: `${artRect.value.height}px`
}))

let resizeObserver
function fitImage() {
  const img = bodyImage.value
  if (!img || !img.naturalWidth || !img.naturalHeight) return
  // 以原版 <img> 已占据的 CSS 盒为准：绝不修改图片宽度、滤镜、混合模式或父容器。
  const boxWidth = img.clientWidth
  const boxHeight = img.clientHeight
  if (!boxWidth || !boxHeight) return
  const imgRatio = img.naturalWidth / img.naturalHeight
  const drawnWidth = Math.min(boxWidth, boxHeight * imgRatio)
  const drawnHeight = drawnWidth / imgRatio
  artRect.value = {
    left: img.offsetLeft + (boxWidth - drawnWidth) / 2,
    top: img.offsetTop + (boxHeight - drawnHeight) / 2,
    width: drawnWidth,
    height: drawnHeight
  }
}
onMounted(() => {
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(fitImage)
    if (stage.value) resizeObserver.observe(stage.value)
    if (bodyImage.value) resizeObserver.observe(bodyImage.value)
  }
  nextTick(fitImage)
})
onBeforeUnmount(() => resizeObserver?.disconnect())
watch(() => props.solo, () => nextTick(fitImage))
</script>

<style scoped>
/* 以下保留用户上传原版 BodyMap2D.vue 的舞台和背景定义，避免视觉回归。 */
.bodymap-wrap { position: relative; width: 100%; }
.bodymap-wrap.solo { height: 100%; display: flex; flex-direction: column; }

.bodymap-inner {
  display: flex;
  gap: 16px;
  align-items: stretch;
  flex: 1;
  min-height: 0;
}
.bodymap-inner.solo { display: block; }
.bodymap-inner.solo .body-stage { width: 100%; height: 100%; min-height: 0; }
.bodymap-inner.solo .body-img { height: 100%; object-fit: contain; }

/* 原版全息人体 + 柔和深蓝光晕垫底：逐项保留，无样式改动 */
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

/* 透明点位层只负责交互定位，不参与图片或背景绘制。 */
.marker-layer { position: absolute; z-index: 2; pointer-events: none; }
.marker { position: absolute; width: 30px; height: 30px; transform: translate(-50%, -50%); padding: 0; border: 0; border-radius: 50%; background: transparent; cursor: pointer; z-index: 2; pointer-events: auto; }
.marker .ring {
  position: absolute;
  left: 6px;
  top: 6px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 2px 6px rgba(31, 58, 104, 0.28);
  transition: transform 0.15s ease;
}
.marker .core {
  position: absolute;
  left: 11px;
  top: 11px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--marker-color);
  box-shadow: 0 0 10px var(--marker-color);
  transition: transform 0.15s ease;
}
.marker:hover .ring, .marker.active .ring { transform: scale(1.35); }
.marker .halo {
  position: absolute;
  left: 3px;
  top: 3px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  opacity: 0;
  background: var(--marker-color);
}
.marker.pulse .halo { opacity: 0.35; animation: pulse 1.6s ease-out infinite; }
@keyframes pulse {
  0% { transform: scale(0.6); opacity: 0.45; }
  70% { transform: scale(1.7); opacity: 0; }
  100% { transform: scale(1.7); opacity: 0; }
}

/* 原版右侧指标网格外观（只有非 solo 使用） */
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
  text-align: left;
  font: inherit;
  box-shadow: 0 4px 14px rgba(31, 58, 104, 0.06);
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.metric-card:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(31, 58, 104, 0.12); }
.metric-card.active { border-color: #7fa8e0; box-shadow: 0 8px 20px rgba(31, 58, 104, 0.16); }
.m-head { display: flex; align-items: center; gap: 6px; min-width: 0; }
.m-head .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; flex: none; }
.m-name { font-size: 12px; color: #7a8aa0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.m-value { margin-top: 4px; font-size: 15px; font-weight: 700; letter-spacing: 0.2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.m-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 4px; }
.m-organ { font-size: 11px; color: #9aa7b8; }
.m-status { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 999px; }
.unmapped { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 10px; padding: 8px 10px; background: #fff; border: 1px dashed #d9e2ef; border-radius: 12px; }
.um-cap { font-size: 11px; color: #9aa7b8; margin-right: 2px; }
.um-chip { display: inline-flex; align-items: center; gap: 5px; font-size: 11.5px; color: #5a6b7d; background: #f5f8fc; border-radius: 999px; padding: 3px 9px; }
.um-chip .dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; flex: none; }
.um-chip b { font-weight: 700; }
.um-chip i { font-style: normal; font-size: 10px; font-weight: 400; color: #9aa7b8; }
.um-st { font-style: normal; font-size: 10.5px; color: #9aa7b8; }
.legend { display: flex; justify-content: center; gap: 12px; font-size: 11.5px; color: #6b7280; margin-top: 10px; }
.legend .dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 4px; }
@media (max-width: 640px) { .bodymap-inner { flex-direction: column; } }
@media (prefers-reduced-motion: reduce) { .marker.pulse .halo { animation: none; } }
.body-image-error { position: absolute; z-index: 4; left: 0; right: 0; bottom: 8px; text-align: center; color: #b91c1c; font-size: 11px; }
</style>
