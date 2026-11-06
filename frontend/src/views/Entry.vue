<template>
  <div>
    <h2 style="margin:0 0 4px;">录入体检</h2>
    <p class="muted">上传报告 / 粘贴原文 / 手动填写，三者任选其一即可 —— 上传或粘贴后直接点「生成健康报告」，不用再填表。</p>

    <div class="card">
      <div class="grid-2">
        <el-card shadow="never">
          <template #header><b>上传体检报告</b></template>
          <div class="muted" style="margin-bottom:8px;">照片、截图、扫描件 PDF；选中后自动识别，保存前请核对结果</div>
          <el-select v-model="checkType" placeholder="检查类型" style="width:100%;max-width:320px;margin-bottom:12px">
            <el-option v-for="t in checkTypes" :key="t.key" :label="t.name" :value="t.key" />
          </el-select>
          <el-upload
            :show-file-list="false"
            :auto-upload="false"
            accept=".png,.jpg,.jpeg,.pdf"
            :on-change="onFileChange"
          >
            <el-button>选择文件</el-button>
          </el-upload>
          <div v-if="fileName" class="muted" style="margin-top:8px;">已选择：{{ fileName }}</div>
          <img v-if="previewUrl" :src="previewUrl" style="margin-top:10px;max-width:260px;border-radius:8px;" />
        </el-card>

        <el-card shadow="never">
          <template #header><b>粘贴体检原文</b></template>
          <div class="muted" style="margin-bottom:8px;">复制体检结论过来，点下方按钮直接分析，无需填表</div>
          <el-input
            v-model="rawText"
            type="textarea"
            :rows="6"
            placeholder="示例：男，24岁，身高176cm，体重72kg，空腹血糖：5.7 mmol/L，甘油三酯TG：2.10 mmol/L，ALT谷丙转氨酶：36 U/L，尿酸：410 μmol/L，收缩压123，舒张压81"
          />
        </el-card>
      </div>

      <el-divider content-position="left">指标核对 / 手动填写</el-divider>
      <el-form label-width="125px">
        <el-alert type="info" :closable="false" style="margin-bottom:16px" title="切换检查类型只筛选输入框，不会清空已填写的项目；没有检测的项目无需填写。" />
        <el-row :gutter="12">
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="性别"><el-select v-model="form.sex" clearable placeholder="未填写"><el-option label="男" value="male"/><el-option label="女" value="female"/></el-select></el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6"><el-form-item label="年龄"><el-input-number v-model="form.age" :min="1" :max="120" controls-position="right" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :md="6"><el-form-item label="身高 (cm)"><el-input-number v-model="form.height" :min="80" :max="230" controls-position="right" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :md="6"><el-form-item label="体重 (kg)"><el-input-number v-model="form.weight" :min="20" :max="200" controls-position="right" /></el-form-item></el-col>
        </el-row>
        <el-alert v-if="hiddenFilledCount" type="info" :closable="false" style="margin-bottom:12px" :title="`其他分类还有 ${hiddenFilledCount} 项已填写指标，保存时会一并提交`" />
        <el-row :gutter="12">
          <el-col v-for="field in visibleFields" :key="field.key" :xs="24" :sm="12" :md="8">
            <el-form-item :label="field.label"><el-input-number v-model="form[field.key]" :min="field.min" :max="field.max" :step="0.1" :precision="2" controls-position="right" style="width:100%" /></el-form-item>
          </el-col>
        </el-row>
        <el-divider content-position="left">其他数值指标（未纳入规则库，不参与自动判读与评分）</el-divider>
        <p class="muted" style="margin:-4px 0 14px">报告识别到但指标库未收录的项目会出现在这里。请核对名称、数值、单位和参考范围。</p>
        <el-row v-for="(item, i) in customMetrics" :key="item.id" :gutter="8" style="margin-bottom:10px">
          <el-col :xs="12" :sm="7"><el-input v-model="item.name" placeholder="指标名称" maxlength="100"><template #prepend v-if="item.auto">识别</template></el-input></el-col>
          <el-col :xs="12" :sm="5"><el-input-number v-model="item.value" :controls="false" placeholder="数值" style="width:100%" /></el-col>
          <el-col :xs="12" :sm="4"><el-input v-model="item.unit" placeholder="单位" maxlength="40" /></el-col>
          <el-col :xs="10" :sm="6"><el-input v-model="item.reference" placeholder="参考范围（选填）" maxlength="100" /></el-col>
          <el-col :xs="2" :sm="2"><el-button type="danger" text @click="customMetrics.splice(i,1)">删除</el-button></el-col>
        </el-row>
        <el-button @click="addCustom">+ 添加自定义指标</el-button>
        <el-form-item label="其他项目" style="margin-top:16px">
          <el-input v-model="extraText" type="textarea" :rows="2" placeholder="非数值项目，例如：心电图窦性心律；腹部 B 超未见明显异常" />
        </el-form-item>
      </el-form>

      <el-button type="primary" size="large" style="width:100%;margin-top:8px;" :loading="saving || recognizing" @click="submit">
        生成健康报告
      </el-button>
      <p class="muted" style="text-align:center;margin-top:10px;">本系统输出仅为健康科普参考，不能替代执业医师诊断。</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const rawText = ref('')
const extraText = ref('')
const saving = ref(false)
const recognizing = ref(false)
const fileName = ref('')
const previewUrl = ref('')
const checkType = ref('general')
const customMetrics = ref([])
const form = reactive({ sex: null, age: null, height: null, weight: null })
const fields = ref([])
const checkTypes = ref([
  { key: 'general', name: '常规体检', keys: ['bmi', 'sbp', 'dbp', 'fast_glucose', 'tg', 'tc', 'alt', 'creatinine'] },
  { key: 'all', name: '全部已支持指标', keys: [] },
  { key: 'blood', name: '血常规', keys: ['hgb', 'wbc', 'plt'] },
  { key: 'liver', name: '肝功能', keys: ['alt', 'ast', 'ggt', 'tbill'] },
  { key: 'kidney', name: '肾功能', keys: ['uric_acid', 'creatinine', 'bun'] },
  { key: 'lipid', name: '血脂检查', keys: ['tg', 'non_hdl', 'tc', 'ldl', 'hdl'] },
  { key: 'glucose', name: '血糖检查', keys: ['fast_glucose', 'hba1c'] },
  { key: 'thyroid', name: '甲状腺检查', keys: ['tsh'] },
  { key: 'endocrine', name: '内分泌科检查', keys: ['fast_glucose', 'hba1c', 'tsh', 'bmi'] },
  { key: 'cardio', name: '血压与体格', keys: ['sbp', 'dbp', 'bmi'] },
  { key: 'other', name: '其他检查', keys: [] }
])
let nextId = 0
let fileObj = null
let recognized = {}
let recognizedSource = null
let recognizedKind = null
let recognitionTask = null
let recognitionVersion = 0

const visibleFields = computed(() => {
  if (checkType.value === 'all') return fields.value
  const type = checkTypes.value.find(t => t.key === checkType.value)
  return fields.value.filter(f => (type?.keys || []).includes(f.key))
})
const hiddenFilledCount = computed(() => {
  const visible = new Set(visibleFields.value.map(f => f.key))
  return fields.value.filter(f => !visible.has(f.key) && form[f.key] != null).length
})
const addCustom = () => customMetrics.value.push({ id: ++nextId, name: '', value: null, unit: '', reference: '', auto: false })

const loadCatalog = async () => {
  const results = await Promise.allSettled([api.metricCatalog(), api.checkTypes()])
  const catalog = results[0].status === 'fulfilled' ? results[0].value : null
  const types = results[1].status === 'fulfilled' ? results[1].value : null
  if (Array.isArray(types?.types)) checkTypes.value = types.types
  if (Array.isArray(catalog?.metrics)) {
    fields.value = catalog.metrics.map(m => ({ key: m.key, label: m.unit ? `${m.name} (${m.unit})` : m.name }))
    for (const f of fields.value) if (!(f.key in form)) form[f.key] = null
    // 异步加载之前已识别的字段也能显示出来。
    for (const [k, v] of Object.entries(recognized)) {
      if (k in form && form[k] == null) form[k] = v
    }
  } else ElMessage.warning('指标目录暂不可用，请检查后端服务')
}
const fillForm = (metrics = {}) => {
  for (const [k, v] of Object.entries(metrics)) {
    if (k === 'sex' && ['male', 'female'].includes(v)) form.sex = v
    else if (k in form && typeof v === 'number' && Number.isFinite(v)) form[k] = v
  }
}
const fillCustom = (items = []) => {
  const manual = customMetrics.value.filter(m => !m.auto)
  const manuallyNamed = new Set(manual.map(m => m.name.trim().toLowerCase()).filter(Boolean))
  const auto = (Array.isArray(items) ? items : []).filter(m => m && m.name && m.value != null)
    .filter(m => !manuallyNamed.has(String(m.name).trim().toLowerCase()))
    .map(m => ({ id: ++nextId, name: String(m.name), value: Number(m.value),
      unit: String(m.unit || ''), reference: String(m.reference || ''), auto: true }))
  customMetrics.value = [...manual, ...auto]
}
const recognize = async (kind) => {
  const source = kind === 'file' ? fileObj : rawText.value.trim()
  if (!source) return
  const version = ++recognitionVersion
  recognizing.value = true
  const task = (async () => {
    try {
      const response = kind === 'file' ? await api.parseFile(source) : await api.parseText(source)
      if (version !== recognitionVersion) return
      recognized = response.metrics || {}
      recognizedSource = source
      recognizedKind = kind
      fillForm(recognized)
      fillCustom(response.custom_metrics || [])
      const count = Object.keys(recognized).length + (response.custom_metrics?.length || 0)
      if (count) ElMessage.success(`识别到 ${count} 项检查数据，请核对后保存`)
      else ElMessage.warning('未识别到数值指标，可手动填写或补充报告描述')
    } catch {
      if (version !== recognitionVersion) return
      recognizedSource = null
      recognizedKind = null
      ElMessage.warning('识别失败；可以手动填写，或稍后重试')
    } finally {
      if (version === recognitionVersion) recognizing.value = false
    }
  })()
  recognitionTask = task
  await task
  if (recognitionTask === task) recognitionTask = null
}
const onFileChange = (uploadFile) => {
  ++recognitionVersion
  fileObj = uploadFile.raw
  fileName.value = uploadFile.name
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = fileObj?.type?.startsWith('image/') ? URL.createObjectURL(fileObj) : ''
  recognized = {}
  recognizedSource = null
  recognizedKind = null
  customMetrics.value = customMetrics.value.filter(m => !m.auto)
  recognize('file')
}
onBeforeUnmount(() => {
  ++recognitionVersion
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
const collectMetrics = () => {
  const out = {}
  for (const [k, v] of Object.entries(form)) {
    if (v === null || v === undefined || v === '') continue
    if (k === 'sex') out.sex = v
    else if (Number.isFinite(Number(v))) out[k] = Number(v)
  }
  return out
}
const getCustom = () => {
  const rows = customMetrics.value.filter(m => m.name.trim() || m.value != null)
  if (rows.some(m => !m.name.trim() || m.value == null || !Number.isFinite(Number(m.value)))) return null
  const signatures = rows.map(m => m.name.trim().toLowerCase())
  if (new Set(signatures).size !== signatures.length) return null
  return rows.map(m => ({ name: m.name.trim(), value: Number(m.value), unit: m.unit.trim(), reference: m.reference.trim() }))
}
const submit = async () => {
  if (saving.value) return
  let custom = getCustom()
  if (custom === null) {
    ElMessage.warning('请补全自定义指标，并检查是否有重复名称'); return
  }
  let manual = collectMetrics()
  const source = fileObj || rawText.value.trim()
  if (!source && !Object.keys(manual).some(k => !['sex', 'age'].includes(k)) && !custom.length && !extraText.value.trim()) {
    ElMessage.warning('请上传报告、粘贴体检原文，或填写至少一项检查数据'); return
  }
  saving.value = true
  try {
    if (recognitionTask) await recognitionTask
    const kind = fileObj ? 'file' : 'text'
    if (source && (recognizedSource !== source || recognizedKind !== kind)) await recognize(kind)
    custom = getCustom()
    if (custom === null) { ElMessage.warning('请核对识别出来的自定义指标'); return }
    manual = collectMetrics()
    const metrics = { ...recognized, ...manual }
    const result = await api.createRecord({ raw_text: rawText.value.trim(), extra_text: extraText.value,
      metrics, check_type: checkType.value, custom_metrics: custom })
    if (result.report_error) ElMessage.warning('指标已保存，AI 解读暂不可用，可在总览页重试')
    else ElMessage.success('报告生成完成')
    router.replace('/overview')
  } catch { /* 全局 API 拦截器会报告接口错误 */ }
  finally { saving.value = false }
}
onMounted(loadCatalog)
</script>
