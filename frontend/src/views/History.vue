<template>
  <div>
    <h2 style="margin:0 0 4px;">历史健康档案</h2>
    <p class="muted">按时间倒序展示每次体检的指标与 AI 总结</p>

    <div v-if="loading" class="card"><el-skeleton :rows="6" animated /></div>

    <div v-else-if="rows.length">
      <el-table :data="rows" border stripe style="width:100%;border-radius:12px;overflow:hidden;">
        <el-table-column prop="record_time" label="体检时间" width="180" />
        <el-table-column prop="check_type_name" label="检查类型" width="135" />
        <el-table-column label="BMI">
          <template #default="{ row }">{{ fmtCell(row.metrics?.bmi) }}</template>
        </el-table-column>
        <el-table-column label="空腹血糖">
          <template #default="{ row }">{{ fmtCell(row.metrics?.fast_glucose) }}</template>
        </el-table-column>
        <el-table-column label="收缩压">
          <template #default="{ row }">{{ fmtCell(row.metrics?.sbp) }}</template>
        </el-table-column>
        <el-table-column label="尿酸">
          <template #default="{ row }">{{ fmtCell(row.metrics?.uric_acid) }}</template>
        </el-table-column>
        <el-table-column label="综合得分" width="110">
          <template #default="{ row }">
            <span>{{ row.score == null ? '—' : row.score }} · {{ row.score_label }}</span>
          </template>
        </el-table-column>
        <el-table-column label="AI 解读" width="100">
          <template #default="{ row }">
            <el-tag :type="row.has_report ? 'success' : 'info'" size="small">
              {{ row.has_report ? '已生成' : '未生成' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="toggle(row.id)">详情</el-button>
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="!row.has_report" link type="success" size="small" :loading="genId === row.id"
                       @click="gen(row)">生成解读</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-for="row in expandedRows" :key="row.id" class="card" style="margin-top:16px;">
        <div class="card-title">体检记录｜{{ row.detail.record_time }} · {{ typeLabel(row.detail.parsed_data?._check_type || row.check_type) }}</div>

        <p style="margin:4px 0;"><b>提取指标：</b></p>
        <div class="metric-tags">
          <el-tag v-for="m in fmtMetrics(row.detail.parsed_data)" :key="m.key" effect="plain" size="small">
            {{ m.label }}：{{ m.value }}
          </el-tag>
        </div>

        <template v-if="row.detail.parsed_data?._custom_metrics?.length">
          <p style="margin:14px 0 6px"><b>其他数值指标（尚未由规则库判读）：</b></p>
          <div class="metric-tags">
            <el-tag v-for="(m, i) in row.detail.parsed_data._custom_metrics" :key="i" type="info" effect="plain" size="small">
              {{ m.name }}：{{ m.value }} {{ m.unit }}<span v-if="m.reference">（参考：{{ m.reference }}）</span> · 未判读
            </el-tag>
          </div>
        </template>

        <template v-if="row.detail.raw_text">
          <p style="margin-top:12px;"><b>原始体检文本：</b></p>
          <div class="muted" style="white-space:pre-wrap;line-height:1.7;">{{ row.detail.raw_text }}</div>
        </template>

        <template v-if="row.detail.report">
          <p style="margin-top:12px;"><b>AI 总结：</b></p>
          <div style="line-height:1.8;">{{ row.detail.report.summary }}</div>
          <ul style="margin:8px 0 0 18px;padding:0;">
            <li v-for="(d, i) in row.detail.report.departments || []" :key="i" style="line-height:1.8;">
              <b>{{ d.name }}</b>：{{ d.comment }}
              <ul v-if="(d.advice || []).length" style="margin:2px 0 0 16px;padding:0;">
                <li v-for="(a, j) in d.advice" :key="j" style="line-height:1.7;">{{ a }}</li>
              </ul>
            </li>
          </ul>
        </template>
      </div>
    </div>

    <div v-else class="card" style="text-align:center;padding:40px;">
      <p class="muted">暂无体检记录，请前往「录入体检」提交数据</p>
      <el-button type="primary" @click="$router.push('/entry')">去录入体检</el-button>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editVisible" :title="'修改记录｜' + editingTime" width="680px" destroy-on-close>
      <div class="muted" style="margin:-8px 0 14px;">修改后会自动重新生成 AI 解读；留空的项会从记录中移除。</div>
      <el-form label-width="150px">
        <el-form-item label="检查类型">
          <el-select v-model="editType" style="width:100%">
            <el-option v-for="t in checkTypes" :key="t.key" :label="t.name" :value="t.key" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12" v-for="f in editFields" :key="f.key">
            <el-form-item :label="f.label">
              <el-select v-if="f.isSex" v-model="editForm[f.key]" placeholder="未填写" clearable style="width:100%">
                <el-option label="男" value="male" />
                <el-option label="女" value="female" />
              </el-select>
              <el-input-number v-else v-model="editForm[f.key]" :min="0" :controls="false"
                               :precision="f.key === 'age' ? 0 : 2" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-divider content-position="left">其他数值指标（不参与自动评分）</el-divider>
        <el-row v-for="(item, i) in editCustom" :key="item.id" :gutter="8" style="margin-bottom:10px">
          <el-col :span="7"><el-input v-model="item.name" placeholder="项目名" maxlength="100" /></el-col>
          <el-col :span="5"><el-input-number v-model="item.value" :controls="false" placeholder="结果" style="width:100%" /></el-col>
          <el-col :span="4"><el-input v-model="item.unit" placeholder="单位" maxlength="40" /></el-col>
          <el-col :span="6"><el-input v-model="item.reference" placeholder="参考区间" maxlength="100" /></el-col>
          <el-col :span="2"><el-button text type="danger" @click="editCustom.splice(i, 1)">移除</el-button></el-col>
        </el-row>
        <el-button @click="addEditCustom">+ 新增其他指标</el-button>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingEdit" @click="saveEdit">保存并重新解读</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(true)
const raw = ref([])
const expanded = ref([])
const details = ref({})
const genId = ref(null)

// 指标库：key -> {name, unit}，用于把指标 key 显示成中文名
const catalog = ref({})
const checkTypes = ref([{ key: 'general', name: '常规体检' }, { key: 'other', name: '其他检查' }])
const typeLabel = (key) => checkTypes.value.find(t => t.key === key)?.name || '未分类' 

// 编辑对话框
const editVisible = ref(false)
const editForm = ref({})
const editType = ref('general')
const editCustom = ref([])
let nextCustomId = 0
const addEditCustom = () => editCustom.value.push({ id: ++nextCustomId, name: '', value: null, unit: '', reference: '' })
const editSource = ref({})
const editingId = ref(null)
const editingTime = ref('')
const savingEdit = ref(false)

const rows = computed(() => [...raw.value].reverse())
// 展开的行带上 detail（原来模板读 row.detail 但从未赋值，导致展开即报错）
const expandedRows = computed(() =>
  rows.value
    .filter((r) => expanded.value.includes(r.id) && details.value[r.id])
    .map((r) => ({ ...r, detail: details.value[r.id] }))
)

const fmtCell = (v) => (v === null || v === undefined || v === '' ? '—' : v)

const labelOf = (key) => {
  if (key === 'sex') return '性别'
  if (key === 'age') return '年龄（岁）'
  if (key === 'height') return '身高（cm）'
  if (key === 'weight') return '体重（kg）'
  const m = catalog.value[key]
  if (m) return m.unit ? `${m.name}（${m.unit}）` : m.name
  return key
}

const fmtVal = (key, value) => {
  if (value === null || value === undefined || value === '') return '—'
  if (key === 'sex') return value === 'male' ? '男' : value === 'female' ? '女' : value
  return value
}

const fmtMetrics = (parsed) => {
  if (!parsed) return []
  const order = { sex: 0, age: 1, height: 2, weight: 3 }
  return Object.keys(parsed)
    .filter((k) => !k.startsWith('_') && parsed[k] !== null && parsed[k] !== undefined && parsed[k] !== '')
    .sort((a, b) => (order[a] ?? 4) - (order[b] ?? 4) || a.localeCompare(b))
    .map((k) => ({ key: k, label: labelOf(k), value: fmtVal(k, parsed[k]) }))
}

const toggle = async (id) => {
  const i = expanded.value.indexOf(id)
  if (i >= 0) {
    expanded.value.splice(i, 1)
    return
  }
  if (!details.value[id]) details.value[id] = await api.getRecord(id)
  expanded.value.push(id)
}

const gen = async (row) => {
  genId.value = row.id
  try {
    await api.genReport(row.id)
    ElMessage.success('解读生成完成')
    details.value[row.id] = await api.getRecord(row.id)
    await load()
  } finally {
    genId.value = null
  }
}

const load = async () => {
  raw.value = await api.listRecords()
}

// 编辑：基础字段 + 记录里已有的指标（BMI 为派生项，不在表单里编辑，保存时自动重算）
const editFields = computed(() => {
  const order = { sex: 0, age: 1, height: 2, weight: 3 }
  return Object.keys(editForm.value)
    .sort((a, b) => (order[a] ?? 4) - (order[b] ?? 4) || a.localeCompare(b))
    .map((key) => ({ key, label: labelOf(key), isSex: key === 'sex' }))
})

const openEdit = (row) => {
  editingId.value = row.id
  editingTime.value = row.record_time
  editSource.value = { ...(row.metrics || {}) }
  const form = { sex: null, age: null, height: null, weight: null }
  for (const [k, v] of Object.entries(editSource.value)) {
    // 元数据包含字符串和对象，绝不能丢进 el-input-number。
    if (k === 'bmi' || k.startsWith('_')) continue
    if (k === 'sex' || (typeof v === 'number' && Number.isFinite(v))) form[k] = v
  }
  editForm.value = form
  editType.value = row.check_type || editSource.value._check_type || 'general'
  editCustom.value = (row.custom_metrics || editSource.value._custom_metrics || [])
    .map(m => ({ id: ++nextCustomId, name: m.name, value: m.value,
      unit: m.unit || '', reference: m.reference || '' }))
  editVisible.value = true
}

const collectEdit = () => {
  const out = {}
  for (const [k, v] of Object.entries(editForm.value)) {
    if (v === null || v === undefined || v === '') continue
    out[k] = k === 'sex' ? v : Number(v)
  }
  // 身高体重齐全时交给后端重算 BMI；否则保留原始 BMI
  if (!(out.height && out.weight) && editSource.value.bmi != null) out.bmi = editSource.value.bmi
  return out
}

const saveEdit = async () => {
  const metrics = collectEdit()
  const rows = editCustom.value.filter(m => m.name.trim() || m.value != null)
  if (rows.some(m => !m.name.trim() || m.value == null || !Number.isFinite(Number(m.value))) ||
    new Set(rows.map(m => m.name.trim().toLowerCase())).size !== rows.length) {
    ElMessage.warning('请核对自定义指标的名称、结果和重复项')
    return
  }
  const custom_metrics = rows.map(m => ({ name: m.name.trim(), value: Number(m.value),
    unit: m.unit.trim(), reference: m.reference.trim() }))
  if (!Object.keys(metrics).some(k => !['sex', 'age'].includes(k)) && !custom_metrics.length) {
    ElMessage.warning('没有可用指标，请至少保留一项')
    return
  }
  savingEdit.value = true
  try {
    const res = await api.updateRecord(editingId.value, { metrics, check_type: editType.value, custom_metrics })
    if (res.report_error) {
      ElMessage.warning(`指标已保存，但 AI 解读重新生成失败（${res.report_error}），可稍后点「生成解读」`)
    } else {
      ElMessage.success('已保存并重新解读')
    }
    editVisible.value = false
    details.value[editingId.value] = await api.getRecord(editingId.value)
    await load()
  } finally {
    savingEdit.value = false
  }
}

const remove = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除这条体检记录吗？删除后不可恢复。', '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    await api.deleteRecord(row.id)
    ElMessage.success('已删除')
    const i = expanded.value.indexOf(row.id)
    if (i >= 0) expanded.value.splice(i, 1)
    delete details.value[row.id]
    await load()
  } catch {
    /* 接口错误已由拦截器提示 */
  }
}

const loadCatalog = async () => {
  const results = await Promise.allSettled([api.metricCatalog(), api.checkTypes()])
  const catalogResponse = results[0].status === 'fulfilled' ? results[0].value : null
  const typeResponse = results[1].status === 'fulfilled' ? results[1].value : null
  if (Array.isArray(catalogResponse?.metrics)) {
    for (const m of catalogResponse.metrics) catalog.value[m.key] = { name: m.name, unit: m.unit || '' }
  }
  if (Array.isArray(typeResponse?.types)) checkTypes.value = typeResponse.types
}

onMounted(async () => {
  await Promise.all([loadCatalog(), load().catch(() => {})])
  loading.value = false
})
</script>

<style scoped>
.metric-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}
</style>
