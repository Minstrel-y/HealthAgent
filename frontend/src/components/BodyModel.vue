<template>
  <div class="body3d-wrap">
    <div ref="stage" class="body3d-stage"></div>
    <div v-if="loadingModel" class="model-loading">3D 模型加载中…</div>

    <div class="legend">
      <span><em class="dot" style="background:#1e7e34;"></em>正常</span>
      <span><em class="dot" style="background:#e67e22;"></em>临界</span>
      <span><em class="dot" style="background:#c0392b;"></em>偏高</span>
      <span><em class="dot" style="background:#9aa7b5;"></em>无数据</span>
    </div>

    <transition name="fade">
      <div v-if="selected" class="marker-tip">
        <b>{{ selected.label }}</b>
        <span class="muted" style="display:block;margin-top:4px;">
          {{ selected.text }}
        </span>
      </div>
    </transition>

    <div class="hint muted">拖拽旋转 · 滚轮缩放 · 点击光点查看指标</div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

const props = defineProps({
  departments: { type: Array, default: () => [] }   // [{name, items:[{key,name,value,unit,status}]}]
})
const emit = defineEmits(['select'])

const stage = ref(null)
const selected = ref(null)
const loadingModel = ref(true)

let renderer, scene, camera, controls, raycaster, rafId, mixer
const markers = []           // { mesh, key, label, text, status }
const markerMeshes = []
let hovered = null

const STATUS_COLOR = { normal: 0x1e7e34, warning: 0xe67e22, danger: 0xc0392b, low: 0x3a8ee6, none: 0x9aa7b5 }

/* ---------- 指标 -> 身体部位 ---------- */
const ANCHORS = [
  { keys: ['sbp', 'dbp'], label: '血压 · 心血管', pos: [0.02, 1.32, 0.13] },
  { keys: ['fast_glucose'], label: '空腹血糖 · 胰腺', pos: [0, 1.12, 0.12] },
  { keys: ['tg', 'non_hdl'], label: '血脂 · 血液', pos: [-0.14, 1.2, 0.08] },
  { keys: ['alt'], label: 'ALT · 肝脏', pos: [0.1, 1.18, 0.1] },
  { keys: ['uric_acid'], label: '尿酸 · 肾脏', pos: [0.11, 1.06, -0.06] },
  { keys: ['creatinine'], label: '肌酐 · 肾脏', pos: [-0.11, 1.06, -0.06] },
  { keys: ['bmi'], label: 'BMI · 整体', pos: [0, 0.86, 0.12] }
]

function statusOf(keys) {
  // 在 departments 里找这些 key 的状态，取最严重的一个
  let worst = 'none'
  const rank = { none: 0, low: 1, normal: 2, warning: 3, danger: 4 }
  let valueText = []
  for (const g of props.departments) {
    for (const it of g.items) {
      if (!keys.includes(it.key)) continue
      if (rank[it.status] > rank[worst]) worst = it.status
      valueText.push(`${it.name} ${it.value}${it.unit ? ' ' + it.unit : ''}（${it.status_label}）`)
    }
  }
  return { status: worst, text: valueText.length ? valueText.join('；') : '本次未检测该项目' }
}

/* ---------- 程序化人体（风格化 low-poly） ---------- */
const SKIN = 0xd8a58f
const MUSCLE = 0xc0392b
const MUSCLE_DARK = 0x992d21

function limb(len, r1, r2, color = MUSCLE) {
  const g = new THREE.CapsuleGeometry(r1, len, 6, 14)
  g.scale(1, 1, r2 / r1 || 1)
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color, roughness: 0.55 }))
  return m
}

function buildBody() {
  const body = new THREE.Group()

  // 躯干：上下略窄的胶囊，压扁一点
  const torso = limb(0.62, 0.17, 0.13)
  torso.scale.set(1.15, 1, 0.62)
  torso.position.y = 1.12
  body.add(torso)

  // 胸肌两块
  for (const sx of [-0.09, 0.09]) {
    const pec = new THREE.Mesh(
      new THREE.SphereGeometry(0.085, 16, 12),
      new THREE.MeshStandardMaterial({ color: MUSCLE_DARK, roughness: 0.5 })
    )
    pec.scale.set(1.1, 0.75, 0.5)
    pec.position.set(sx, 1.32, 0.085)
    body.add(pec)
  }

  // 腹肌六块（装饰，浅色）
  const abMat = new THREE.MeshStandardMaterial({ color: MUSCLE, roughness: 0.6 })
  for (let r = 0; r < 2; r++) {
    for (const sx of [-0.055, 0.055]) {
      const ab = new THREE.Mesh(new THREE.SphereGeometry(0.045, 12, 10), abMat)
      ab.scale.set(1.1, 0.8, 0.5)
      ab.position.set(sx, 1.06 - r * 0.1, 0.1)
      body.add(ab)
    }
  }

  // 头 + 颈
  const head = new THREE.Mesh(
    new THREE.SphereGeometry(0.13, 20, 16),
    new THREE.MeshStandardMaterial({ color: SKIN, roughness: 0.65 })
  )
  head.scale.set(0.88, 1.1, 0.95)
  head.position.y = 1.62
  body.add(head)
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.055, 0.09, 10),
    new THREE.MeshStandardMaterial({ color: SKIN, roughness: 0.65 }))
  neck.position.y = 1.49
  body.add(neck)

  // 手臂：上臂+前臂，自然下垂微张
  for (const s of [-1, 1]) {
    const upper = limb(0.26, 0.055, 0.05)
    upper.position.set(0.245 * s, 1.24, 0)
    upper.rotation.z = 0.16 * s
    body.add(upper)
    const fore = limb(0.24, 0.042, 0.038)
    fore.position.set(0.31 * s, 0.98, 0.01)
    fore.rotation.z = 0.05 * s
    body.add(fore)
    const hand = new THREE.Mesh(new THREE.SphereGeometry(0.045, 10, 8),
      new THREE.MeshStandardMaterial({ color: SKIN, roughness: 0.7 }))
    hand.scale.set(0.8, 1.15, 0.5)
    hand.position.set(0.335 * s, 0.83, 0.015)
    body.add(hand)
    // 三角肌
    const delt = new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 10),
      new THREE.MeshStandardMaterial({ color: MUSCLE_DARK, roughness: 0.5 }))
    delt.position.set(0.19 * s, 1.38, 0)
    body.add(delt)
  }

  // 腿：大腿+小腿
  for (const s of [-1, 1]) {
    const thigh = limb(0.34, 0.085, 0.075)
    thigh.position.set(0.085 * s, 0.68, 0)
    body.add(thigh)
    const calf = limb(0.32, 0.06, 0.045)
    calf.position.set(0.085 * s, 0.28, 0.005)
    body.add(calf)
    const foot = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.05, 0.2),
      new THREE.MeshStandardMaterial({ color: SKIN, roughness: 0.7 }))
    foot.position.set(0.085 * s, 0.025, 0.045)
    body.add(foot)
  }

  return body
}

/* ---------- 标记点 ---------- */
function buildMarkers() {
  for (const a of ANCHORS) {
    const { status, text } = statusOf(a.keys)
    const color = STATUS_COLOR[status]
    const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.95 })
    const dot = new THREE.Mesh(new THREE.SphereGeometry(0.022, 12, 12), mat)
    dot.position.set(...a.pos)

    // 外圈光环（异常时呼吸动画）
    const halo = new THREE.Mesh(
      new THREE.SphereGeometry(0.035, 12, 12),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: status === 'normal' || status === 'none' ? 0.12 : 0.35 })
    )
    dot.add(halo)

    dot.userData = { key: a.keys.join(','), label: a.label, text, status, halo, baseScale: 1 }
    scene.add(dot)
    markers.push(dot.userData)
    markerMeshes.push(dot)
  }
}

/* ---------- 加载真实人形 GLB（Xbot），失败回退程序化人体 ---------- */
function loadHuman() {
  const loader = new GLTFLoader()
  loader.load(
    '/models/xbot.glb',
    (gltf) => {
      const model = gltf.scene

      // 归一化：整体高度缩放到 1.72，脚底贴地
      const box = new THREE.Box3().setFromObject(model)
      const size = new THREE.Vector3()
      box.getSize(size)
      model.scale.setScalar(1.72 / size.y)
      const box2 = new THREE.Box3().setFromObject(model)
      model.position.y = -box2.min.y

      // 转到正面稍侧，避免完全正对显得呆板
      model.rotation.y = 0.12

      scene.add(model)
      loadingModel.value = false

      // 待机呼吸动画（Xbot 自带 idle）
      if (gltf.animations && gltf.animations.length) {
        mixer = new THREE.AnimationMixer(model)
        const idle = gltf.animations.find((a) => /idle/i.test(a.name)) || gltf.animations[0]
        mixer.clipAction(idle).play()
      }
    },
    undefined,
    () => {
      // 加载失败 → 回退程序化人体
      scene.add(buildBody())
      loadingModel.value = false
    }
  )
}

function refreshMarkers() {
  // departments 变化后重建标记状态
  for (const m of markerMeshes) scene.remove(m)
  markers.length = 0
  markerMeshes.length = 0
  buildMarkers()
}

/* ---------- 场景 ---------- */
function init() {
  const el = stage.value
  const w = el.clientWidth, h = el.clientHeight

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
  renderer.setSize(w, h)
  el.appendChild(renderer.domElement)

  scene = new THREE.Scene()

  camera = new THREE.PerspectiveCamera(38, w / h, 0.1, 50)
  camera.position.set(0, 1.25, 3.1)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.target.set(0, 1.05, 0)
  controls.enableDamping = true
  controls.minDistance = 1.6
  controls.maxDistance = 5
  controls.enablePan = false

  scene.add(new THREE.HemisphereLight(0xffffff, 0x668899, 1.15))
  const key = new THREE.DirectionalLight(0xffffff, 1.6)
  key.position.set(2, 3, 2.5)
  scene.add(key)
  const rim = new THREE.DirectionalLight(0x88bbff, 0.7)
  rim.position.set(-2.5, 1.5, -2)
  scene.add(rim)

  // 地面圆盘 + 阴影感
  const disc = new THREE.Mesh(
    new THREE.CylinderGeometry(0.62, 0.66, 0.03, 40),
    new THREE.MeshStandardMaterial({ color: 0xdfe9f3, roughness: 0.9 })
  )
  disc.position.y = -0.02
  scene.add(disc)

  loadHuman()
  buildMarkers()

  raycaster = new THREE.Raycaster()
  const pointer = new THREE.Vector2()
  let downPos = null

  const onDown = (e) => { downPos = [e.clientX, e.clientY] }
  const onUp = (e) => {
    if (!downPos) return
    const moved = Math.hypot(e.clientX - downPos[0], e.clientY - downPos[1])
    downPos = null
    if (moved > 6) return   // 拖拽不算点击
    const rect = renderer.domElement.getBoundingClientRect()
    pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
    pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1
    raycaster.setFromCamera(pointer, camera)
    const hit = raycaster.intersectObjects(markerMeshes, false)[0]
    if (hit) {
      const d = hit.object.userData
      selected.value = d
      emit('select', d)
    } else {
      selected.value = null
    }
  }
  renderer.domElement.addEventListener('pointerdown', onDown)
  renderer.domElement.addEventListener('pointerup', onUp)

  const clock = new THREE.Clock()
  const animate = () => {
    rafId = requestAnimationFrame(animate)
    const dt = clock.getDelta()
    mixer?.update(dt)   // 待机动画
    const t = clock.getElapsedTime()
    // 异常标记呼吸动画
    for (const m of markers) {
      if (m.status === 'warning' || m.status === 'danger') {
        const s = 1 + 0.18 * Math.sin(t * 3)
        m.halo.scale.setScalar(s)
      }
    }
    controls.update()
    renderer.render(scene, camera)
  }
  animate()

  const ro = new ResizeObserver(() => {
    const w2 = el.clientWidth, h2 = el.clientHeight
    if (!w2 || !h2) return
    camera.aspect = w2 / h2
    camera.updateProjectionMatrix()
    renderer.setSize(w2, h2)
  })
  ro.observe(el)
}

onMounted(() => { init() })

watch(() => props.departments, refreshMarkers, { deep: true })

onBeforeUnmount(() => {
  cancelAnimationFrame(rafId)
  renderer?.dispose()
})

defineExpose({ selected })
</script>

<style scoped>
.body3d-wrap { position: relative; width: 100%; height: 420px; }
.body3d-stage { width: 100%; height: 100%; cursor: grab; }
.body3d-stage:active { cursor: grabbing; }

.legend {
  position: absolute;
  left: 12px;
  top: 10px;
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #6b7280;
  background: rgba(255, 255, 255, 0.75);
  padding: 4px 10px;
  border-radius: 999px;
}
.legend .dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-right: 4px;
}

.marker-tip {
  position: absolute;
  right: 12px;
  top: 12px;
  max-width: 240px;
  background: #fff;
  border: 1px solid #e6efff;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 13px;
  box-shadow: 0 6px 18px rgba(15, 76, 129, 0.12);
}
.marker-tip b { color: #0f4c81; }

.hint {
  position: absolute;
  bottom: 6px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 12px;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.model-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  font-size: 13px;
  pointer-events: none;
}
</style>
