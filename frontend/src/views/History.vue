<template>
  <div>
    <h2 style="margin:0 0 4px;">历史健康档案</h2>
    <p class="muted">按时间倒序展示每次体检的指标与 AI 总结</p>

    <div v-if="loading" class="card"><el-skeleton :rows="6" animated /></div>

    <div v-else-if="rows.length">
      <el-table :data="rows" border stripe style="width:100%;border-radius:12px;overflow:hidden;">
        <el-table-column prop="record_time" label="体检时间" width="180" />
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
            <span>{{ row.score }} · {{ row.score_label }}</span>
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
        <div class="card-title">体检记录｜{{ row.detail.record_time }}</div>

        <p style="margin:4px 0;"><b>提取指标：</b></p>
        <div class="metric-tags">
          <el-tag v-for="m in fmtMetrics(row.detail.parsed_data)" :key="m.key" effect="plain" size="small">
            {{ m.label }}：{{ m.value }}
          </el-tag>
        </div>

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

// 编辑对话框
const editVisible = ref(false)
const editForm = ref({})
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
    .filter((k) => parsed[k] !== null && parsed[k] !== undefined && parsed[k] !== '')
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
    if (k === 'bmi') continue
    form[k] = v
  }
  editForm.value = form
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
  if (!Object.keys(metrics).length) {
    ElMessage.warning('没有可用指标，请至少保留一项')
    return
  }
  savingEdit.value = true
  try {
    const res = await api.updateRecord(editingId.value, { metrics })
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
  try {
    const res = await api.metricCatalog()
    const list = res?.metrics
    if (Array.isArray(list)) {
      for (const m of list) catalog.value[m.key] = { name: m.name, unit: m.unit || '' }
    }
  } catch {
    /* 标签回退为原始 key */
  }
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
