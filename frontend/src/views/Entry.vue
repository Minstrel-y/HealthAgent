<template>
  <div>
    <h2 style="margin:0 0 4px;">录入体检</h2>
    <p class="muted">上传报告 / 粘贴原文 / 手动填写，三者任选其一即可 —— 上传或粘贴后直接点「生成健康报告」，不用再填表。</p>

    <div class="card">
      <div class="grid-2">
        <el-card shadow="never">
          <template #header><b>上传体检报告</b></template>
          <div class="muted" style="margin-bottom:8px;">照片、截图、扫描件 PDF，选好后自动识别</div>
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

      <el-divider content-position="left">
        <span class="muted">指标核对 / 手动填写（上传或粘贴时不需要填，做过的项目填多少都可以）</span>
      </el-divider>

      <el-form label-width="130px">
        <el-row :gutter="12">
          <el-col :span="6">
            <el-form-item label="性别">
              <el-select v-model="form.sex" placeholder="未填写" clearable>
                <el-option label="男" value="male" />
                <el-option label="女" value="female" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="年龄"><el-input-number v-model="form.age" :min="1" :max="120" controls-position="right" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="身高 (cm)"><el-input-number v-model="form.height" :min="80" :max="230" controls-position="right" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="体重 (kg)"><el-input-number v-model="form.weight" :min="20" :max="200" controls-position="right" /></el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col v-for="f in fields" :key="f.key" :span="6">
            <el-form-item :label="f.label">
              <el-input-number v-model="form[f.key]" :min="f.min" :max="f.max" :step="0.1" :precision="2" controls-position="right" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="其他项目">
          <el-input
            v-model="extraText"
            type="textarea"
            :rows="2"
            placeholder="上面没覆盖到的项目，例如：血常规 WBC 6.2×10⁹/L；心电图窦性心律；腹部B超未见明显异常"
          />
        </el-form-item>
      </el-form>

      <el-button type="primary" size="large" style="width:100%;margin-top:8px;" :loading="saving" @click="submit">
        生成健康报告
      </el-button>
      <p class="muted" style="text-align:center;margin-top:10px;">本系统输出仅为健康科普参考，不能替代执业医师诊断。</p>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const rawText = ref('')
const extraText = ref('')
const saving = ref(false)
const fileName = ref('')
const previewUrl = ref('')
let fileObj = null

const form = reactive({
  sex: null, age: null, height: null, weight: null,
  sbp: null, dbp: null, fast_glucose: null, tg: null,
  non_hdl: null, alt: null, uric_acid: null, creatinine: null
})

// 字段来自后端指标库：指标库新增一项，录入表单就多一个输入框，前端不用改代码
const fields = ref([
  { key: 'sbp', label: '收缩压 mmHg', min: 60, max: 250 },
  { key: 'dbp', label: '舒张压 mmHg', min: 30, max: 160 },
  { key: 'fast_glucose', label: '空腹血糖 mmol/L', min: 1, max: 40 },
  { key: 'tg', label: '甘油三酯 mmol/L', min: 0.1, max: 25 },
  { key: 'non_hdl', label: '非高密度脂蛋白', min: 0.1, max: 20 },
  { key: 'alt', label: 'ALT U/L', min: 1, max: 800 },
  { key: 'uric_acid', label: '尿酸 μmol/L', min: 50, max: 1200 },
  { key: 'creatinine', label: '肌酐 μmol/L', min: 10, max: 1000 }
])

const loadCatalog = async () => {
  try {
    const res = await api.metricCatalog()
    const list = res?.metrics
    if (!Array.isArray(list) || !list.length) return
    fields.value = list.map((m) => ({
      key: m.key,
      label: m.unit ? `${m.name} ${m.unit}` : m.name,
      // 上限取参考值上限的 10 倍并保底 999，保证病理值也能填进去
      min: 0,
      max: Math.max(999, Math.ceil((m.high || 100) * 10))
    }))
    for (const f of fields.value) {
      if (!(f.key in form)) form[f.key] = null
    }
  } catch {
    /* 接口不可用时沿用上面的默认字段 */
  }
}

const fillForm = (metrics = {}) => {
  for (const k of Object.keys(form)) {
    if (metrics[k] !== undefined && metrics[k] !== null) form[k] = metrics[k]
  }
}

const recognize = async (source) => {
  try {
    const res = source === 'file'
      ? await api.parseFile(fileObj)
      : await api.parseText(rawText.value)
    if (Object.keys(res.metrics || {}).length) {
      fillForm(res.metrics)
      ElMessage.success(`已识别 ${Object.keys(res.metrics).length} 项指标（来源：${res.source}），核对后点下方按钮生成报告`)
    } else {
      ElMessage.warning('没识别到指标，可手动填写或在补充说明里描述')
    }
  } catch (e) {
    ElMessage.error('识别失败，请稍后重试或手动填写')
  }
}

const onFileChange = (uploadFile) => {
  fileObj = uploadFile.raw
  fileName.value = uploadFile.name
  previewUrl.value = fileObj.type?.startsWith('image/') ? URL.createObjectURL(fileObj) : ''
  recognize('file')
}

const collectMetrics = () => {
  const out = {}
  for (const k of Object.keys(form)) {
    if (form[k] !== null && form[k] !== undefined && form[k] !== '') out[k] = Number(form[k])
  }
  return out
}

const submit = async () => {
  const manual = collectMetrics()
  const manualCount = Object.keys(manual).filter((k) => !['sex', 'age'].includes(k)).length
  if (!rawText.value.trim() && !manualCount && !extraText.value.trim() && !fileObj) {
    ElMessage.warning('请上传报告、粘贴体检原文，或填写至少一项指标')
    return
  }
  saving.value = true
  try {
    let metrics = manual
    let raw = rawText.value.trim()

    // 上传文件 → OCR；粘贴原文 → 模型抽取（失败降级本地正则）：都不需要手动再填一遍
    if (fileObj) {
      const p = await api.parseFile(fileObj)
      if (Object.keys(p.metrics || {}).length) metrics = { ...p.metrics, ...manual }
      ElMessage.info(`已识别 ${Object.keys(p.metrics || {}).length} 项指标`)
    } else if (raw) {
      const p = await api.parseText(raw)
      if (Object.keys(p.metrics || {}).length) metrics = { ...p.metrics, ...manual }
      ElMessage.info(`已识别 ${Object.keys(p.metrics || {}).length} 项指标（${p.source}）`)
    }

    const res = await api.createRecord({ raw_text: raw, extra_text: extraText.value, metrics })
    if (res.report_error) {
      ElMessage.warning(`AI 解读暂未生成（${res.report_error}），指标已保存，可在总览页重试`)
    } else {
      ElMessage.success('报告生成完成')
    }
    router.replace('/overview')
  } finally {
    saving.value = false
  }
}

onMounted(loadCatalog)
</script>
