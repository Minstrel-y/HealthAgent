/**
 * 人体交互入口采用「身体系统」而非「一个指标一个点」。
 * x/y 是相对于 body_render.png 实际可见图片的百分比（非外层容器）。
 * 只关联已经确切登记的指标键，未知自定义项不猜测所属器官。
 */
export const BODY_SYSTEMS = Object.freeze([
  { key: 'thyroid', label: '甲状腺', area: '颈部', x: 49.5, y: 20.5, hint: '甲状腺相关检验' },
  { key: 'cardio', label: '心血管', area: '胸部', x: 50.5, y: 30.0, hint: '血压与心肌相关检查；LDH 非心肌特异性，点位只是导航入口' },
  { key: 'blood', label: '血液 / 造血', area: '胸骨示意区', x: 42.5, y: 31.5, hint: '血常规为全身循环血液检查，光点仅是导航入口' },
  { key: 'lipid', label: '血脂代谢', area: '胸部示意区', x: 58.0, y: 34.2, hint: '血脂属于全身代谢指标，并不代表局部器官状态' },
  { key: 'liver', label: '肝脏', area: '上腹部', x: 43.0, y: 41.5, hint: '肝功能相关检验' },
  { key: 'pancreas', label: '糖代谢', area: '上腹部示意区', x: 51.0, y: 43.0, hint: '血糖相关指标不等同于胰腺结构或功能诊断' },
  { key: 'kidney', label: '肾脏 / 肾功能', area: '腰腹部', x: 57.0, y: 47.3, hint: '左右肾共用一个肾功能入口，无法由常规血检区分左右肾' },
  { key: 'body', label: '体格指标', area: '整体示意区', x: 49.5, y: 58.0, hint: 'BMI 为全身体格指标' }
])

const METRIC_SYSTEM = {
  tsh: 'thyroid', ft3: 'thyroid', ft4: 'thyroid',
  sbp: 'cardio', dbp: 'cardio', ldh: 'cardio', ctnt: 'cardio',
  hgb: 'blood', wbc: 'blood', plt: 'blood',
  rbc: 'blood', hct: 'blood', mcv: 'blood', mch: 'blood', mchc: 'blood',
  tg: 'lipid', non_hdl: 'lipid', tc: 'lipid', ldl: 'lipid', hdl: 'lipid',
  alt: 'liver', ast: 'liver', ggt: 'liver', tbill: 'liver',
  pa: 'liver', tp: 'liver', alb: 'liver', dbil: 'liver', alp: 'liver', tba: 'liver', che: 'liver', ibil: 'liver',
  fast_glucose: 'pancreas', hba1c: 'pancreas',
  uric_acid: 'kidney', creatinine: 'kidney', bun: 'kidney', beta2_mg: 'kidney',
  bmi: 'body'
}

const GROUP_ALIAS = { kidney_l: 'kidney', kidney_r: 'kidney' }
const SEVERITY = { none: 0, normal: 1, low: 2, warning: 3, danger: 4 }

export function systemForItem(item) {
  const mappedKey = METRIC_SYSTEM[item?.key]
  if (mappedKey) return mappedKey
  // 将旧版后端双肾锚点统一归入一个肾功能入口。
  const group = item?.anchor?.group
  const normalized = GROUP_ALIAS[group] || group
  return BODY_SYSTEMS.some(s => s.key === normalized) ? normalized : null
}

export function buildSystemViews(departments = []) {
  const systems = BODY_SYSTEMS.map(s => ({ ...s, keys: s.key, items: [], status: 'none', measured: 0, abnormal: 0, unrated: 0 }))
  const byKey = new Map(systems.map(s => [s.key, s]))
  const seen = new Set()
  for (const department of departments) {
    for (const item of department.items || []) {
      if (!item || seen.has(item.key)) continue
      seen.add(item.key)
      const system = byKey.get(systemForItem(item))
      if (system) system.items.push(item)
    }
  }
  for (const system of systems) {
    system.measured = system.items.length
    system.abnormal = system.items.filter(i => ['danger', 'warning', 'low'].includes(i.status) && i.known !== false).length
    system.unrated = system.items.filter(i => i.status === 'none' || i.known === false).length
    const known = system.items.filter(i => i.known !== false && SEVERITY[i.status] > 0)
    if (known.length) {
      system.status = known.reduce((status, i) => SEVERITY[i.status] > SEVERITY[status] ? i.status : status, 'normal')
    } else if (system.items.length) {
      system.status = 'unrated'
    }
  }
  return systems
}

export const STATUS_COLOR = {
  normal: '#059669', warning: '#d97706', danger: '#dc2626',
  low: '#2563eb', none: '#94a3b8', unrated: '#64748b'
}
export const STATUS_TEXT = {
  normal: '已测 · 正常', warning: '已测 · 临界', danger: '已测 · 偏高',
  low: '已测 · 偏低', none: '未检测', unrated: '已测 · 未判读'
}
