<template>
  <div class="staff-page">
    <div class="staff-head">
      <div>
        <h2>{{ pageTitle }}</h2>
        <p>{{ isAdmin ? '用户与报告管理 · 数据修正 · 审计追踪' : '患者档案 · 报告审阅 · 临床诊断与复查' }}</p>
      </div>
      <el-tag :type="isAdmin ? 'warning' : 'success'" effect="plain">{{ isAdmin ? '管理员' : '医生' }}</el-tag>
    </div>

    <div v-if="loadingProfile" class="card">正在读取账号权限…</div>
    <div v-else-if="!authorized" class="card">当前账号没有访问工作台的权限。</div>
    <template v-else>
      <section v-if="section === 'dashboard'" class="staff-dashboard">
        <div class="card staff-summary"><b>{{ isAdmin ? '账户总览' : '患者总览' }}</b><strong>{{ patients.length }}</strong><small>{{ isAdmin ? '可管理账号' : '可查看患者' }}</small></div>
        <div class="card staff-summary"><b>当前选中</b><strong>{{ records.length }}</strong><small>该账号体检报告数</small></div>
        <div class="card staff-summary"><b>{{ isAdmin ? '数据管理' : '诊断管理' }}</b><strong>{{ isAdmin ? '管理员' : '医生' }}</strong><small>{{ isAdmin ? '只修改数据，不签署诊断' : '只追加诊断，不修改数据' }}</small></div>
      </section>
      <section v-if="section === 'audit' && isAdmin" class="card" style="margin-bottom:16px">
        <div class="flex-between"><b>管理员操作日志</b><el-button size="small" @click="loadAudit">刷新</el-button></div>
        <el-table :data="auditLogs" size="small" stripe max-height="560">
          <el-table-column prop="created_at" label="时间" min-width="165" />
          <el-table-column prop="actor_username" label="操作人" min-width="110" />
          <el-table-column prop="action" label="操作类型" min-width="180" />
          <el-table-column prop="target_username" label="目标用户" min-width="120" />
          <el-table-column prop="record_id" label="记录编号" width="100" />
        </el-table>
        <el-empty v-if="!auditLogs.length" description="暂无操作记录" />
      </section>
      <div v-if="section !== 'audit'" class="staff-layout">
      <aside class="card staff-list">
        <div class="staff-section-title">{{ isAdmin ? '全部账号' : '患者列表' }}</div>
        <el-input v-model="keyword" clearable placeholder="搜索账号或姓名" @keyup.enter="loadPatients">
          <template #append><el-button @click="loadPatients">搜索</el-button></template>
        </el-input>
        <el-scrollbar max-height="560px" class="patients-scroll">
          <div v-for="person in patients" :key="person.username" role="button" tabindex="0"
                  class="patient-row" :class="{ picked: selectedUser === person.username }"
                  @click="choosePatient(person.username)" @keydown.enter="choosePatient(person.username)">
            <span class="patient-name">{{ person.nickname || person.username }}</span>
            <small>{{ person.username }} · {{ roleText(person.role) }}</small>
            <el-select v-if="isAdmin && section === 'users'" :model-value="person.role" size="small"
                       :disabled="person.username === accountUsername"
                       class="role-change" @click.stop @change="changePatientRole(person, $event)">
              <el-option label="普通用户" value="user"/>
              <el-option label="医生" value="doctor"/>
              <el-option label="管理员" value="admin"/>
            </el-select>
          </div>
          <el-empty v-if="!patients.length" description="没有可查看的患者" :image-size="64" />
        </el-scrollbar>
      </aside>

      <main class="staff-main">
        <section v-if="section !== 'users'" class="card">
          <div class="staff-section-title">{{ selectedUser ? `${selectedUser} · 体检档案` : '请选择左侧患者' }}</div>
          <el-table v-if="selectedUser" :data="records" size="small" stripe
                    highlight-current-row @row-click="selectRecord">
            <el-table-column prop="record_time" label="保存时间" min-width="155" />
            <el-table-column label="检查类型" min-width="130">
              <template #default="{ row }">{{ checkTypeName(row.parsed_data?._check_type) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="88">
              <template #default="{ row }"><el-button link type="primary" @click.stop="selectRecord(row)">查看</el-button></template>
            </el-table-column>
          </el-table>
          <el-empty v-if="selectedUser && !records.length" description="该账号暂无体检记录" :image-size="70" />
          <p v-if="isAdmin && selectedUser && section !== 'users'" class="hint">管理员可修改或删除选中的体检记录；医生无此权限。</p>
        </section>

        <section v-if="section === 'trends' && selectedUser" class="card">
          <div class="staff-section-title">{{ selectedUser }} · 历史指标走势（原始数值）</div>
          <el-select v-model="trendMetric" filterable placeholder="选择指标" style="width:260px;margin-bottom:12px">
            <el-option v-for="item in metricOptions" :key="item.key" :label="item.name" :value="item.key" />
          </el-select>
          <el-table :data="trendRows" stripe size="small">
            <el-table-column prop="date" label="记录日期" min-width="175"/>
            <el-table-column prop="value" label="检测结果" min-width="130"/>
          </el-table>
          <p class="hint">历史数据仅供医生参考，不自动给出确诊结论。</p>
        </section>
        <template v-if="selectedRecord && section !== 'users' && section !== 'trends'">
          <section v-if="section !== 'trends'" class="card">
            <div class="flex-between">
              <div class="staff-section-title">体检记录 #{{ selectedRecord.id }} <el-tag size="small" type="info">原始记录</el-tag></div>
              <div v-if="isAdmin && section === 'dashboard'" class="action-group">
                <el-button size="small" @click="openEditor">修改数据</el-button>
                <el-button size="small" plain @click="regenerateReport">重新生成 AI 解读</el-button>
                <el-button size="small" type="danger" plain @click="removeRecord">删除</el-button>
              </div>
            </div>
            <el-table :data="metricRows" size="small" max-height="280" stripe>
              <el-table-column prop="name" label="项目" min-width="150" />
              <el-table-column prop="value" label="结果" min-width="90" />
              <el-table-column prop="unit" label="单位" min-width="110" />
              <el-table-column prop="reference" label="参考范围" min-width="130" />
            </el-table>
            <div v-if="selectedRecord.raw_text" class="report-original">
              <b>原始报告文本</b>
              <el-scrollbar max-height="150px"><pre>{{ selectedRecord.raw_text }}</pre></el-scrollbar>
            </div>
          </section>

          <section v-if="!isAdmin && ['reports', 'dashboard'].includes(section)" class="card">
            <div class="staff-section-title">{{ isAdmin ? '已有医生诊断（只读）' : '医生诊断与复查意见' }}</div>
            <el-alert v-if="!isAdmin" title="此处保存的是人工填写的医生意见，不会更改原始体检指标。开发阶段账号资质未核验。"
                      type="info" :closable="false" show-icon />
            <el-form v-if="!isAdmin && section === 'dashboard'" label-position="top" class="diagnosis-form" @submit.prevent="saveDiagnosis">
              <el-form-item label="诊断标题"><el-input v-model.trim="diagnosis.title" maxlength="120" /></el-form-item>
              <el-form-item label="临床评估"><el-input v-model.trim="diagnosis.impression" type="textarea" :rows="3" maxlength="4000" /></el-form-item>
              <el-form-item label="处理及健康建议"><el-input v-model.trim="diagnosis.advice" type="textarea" :rows="3" maxlength="4000" /></el-form-item>
              <el-form-item label="复查建议"><el-input v-model.trim="diagnosis.follow_up" type="textarea" :rows="2" maxlength="2000" /></el-form-item>
              <el-button type="primary" :loading="saving" @click="saveDiagnosis">提交诊断意见</el-button>
            </el-form>
            <el-divider />
            <div v-for="item in diagnoses" :key="item.id" class="diagnosis-item">
              <strong>{{ item.title }}</strong>
              <span>{{ item.doctor_username }} · {{ item.created_at }}</span>
              <p>{{ item.impression }}</p>
              <p><b>建议：</b>{{ item.advice }}</p>
              <p v-if="item.follow_up"><b>复查：</b>{{ item.follow_up }}</p>
            </div>
            <el-empty v-if="!diagnoses.length" description="尚未添加医生诊断" :image-size="66" />
          </section>
        </template>
      </main>
    </div>
    </template>

    <el-dialog v-model="editorVisible" title="管理员修改体检数据" width="680px" append-to-body>
      <p class="hint">只调整原始数据；保存后旧 AI 解读会失效，需要手动重新生成。</p>
      <div class="edit-scroll">
        <el-form label-position="top">
          <el-form-item label="性别">
            <el-select v-model="editSex" placeholder="未提供" clearable style="width:100%">
              <el-option value="male" label="男"/><el-option value="female" label="女"/>
            </el-select>
          </el-form-item>
          <el-form-item label="年龄"><el-input-number v-model="editAge" :min="0" :max="129" style="width:100%" /></el-form-item>
          <div class="staff-section-title">结构化数值指标</div>
          <div v-for="(field, index) in editRows" :key="index" class="edit-line">
            <el-select v-model="field.key" filterable placeholder="指标名称">
              <el-option v-for="opt in metricOptions" :key="opt.key" :value="opt.key" :label="opt.name" />
            </el-select>
            <el-input v-model="field.value" placeholder="数值" />
            <el-button type="danger" plain @click="editRows.splice(index,1)">删除</el-button>
          </div>
          <el-button plain @click="editRows.push({ key: '', value: '' })">新增指标</el-button>
          <div class="staff-section-title extra-section">自定义项目</div>
          <div v-for="(field, index) in editCustom" :key="index" class="edit-line">
            <el-input v-model="field.name" placeholder="名称" />
            <el-input v-model="field.value" placeholder="数值" />
            <el-input v-model="field.unit" placeholder="单位" />
            <el-button type="danger" plain @click="editCustom.splice(index,1)">删除</el-button>
          </div>
          <el-button plain @click="editCustom.push({name:'',value:'',unit:'',reference:''})">新增自定义项目</el-button>
          <el-form-item label="原始文本" class="extra-section">
            <el-input v-model="editRaw" type="textarea" :rows="3" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="editorVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveAdminEdit">保存数据</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { auth, api, staffApi } from '../api/index.js'

const route = useRoute()
const section = computed(() => route.meta.section || 'dashboard')
const pageTitle = computed(() => route.meta.title || '工作台')
const role = ref('user')
const accountUsername = ref('')
const loadingProfile = ref(true)
const authorized = computed(() => ['doctor', 'admin'].includes(role.value) && route.path.startsWith('/' + role.value + '/'))
const isAdmin = computed(() => role.value === 'admin')
const keyword = ref('')
const patients = ref([])
const selectedUser = ref('')
const records = ref([])
const selectedRecord = ref(null)
const diagnoses = ref([])
const catalog = ref([])
const checkTypes = ref({})
const auditLogs = ref([])
const trendMetric = ref('fast_glucose')
const trendRows = computed(() => records.value.slice().reverse().filter(r => typeof r.parsed_data?.[trendMetric.value] === 'number').map(r => ({date: r.record_time, value: r.parsed_data[trendMetric.value]})))
const saving = ref(false)
const editorVisible = ref(false)
const editRows = ref([])
const editCustom = ref([])
const editRaw = ref('')
const editSex = ref('')
const editAge = ref(null)
const diagnosis = reactive({ title: '', impression: '', advice: '', follow_up: '' })
const roleText = (r) => ({ user: '用户', doctor: '医生', admin: '管理员' })[r] || r
const metricOptions = computed(() => [
  { key: 'height', name: '身高（cm）' }, { key: 'weight', name: '体重（kg）' },
  ...catalog.value.map(x => ({ key: x.key, name: `${x.name}（${x.unit || '无单位'}）` }))
])
const metricName = (key) => metricOptions.value.find(x => x.key === key)?.name?.split('（')[0] || key
const checkTypeName = (k) => checkTypes.value[k] || k || '未分类'
const metricRows = computed(() => {
  const data = selectedRecord.value?.parsed_data || {}
  const rows = Object.entries(data)
    .filter(([k,v]) => !k.startsWith('_') && !['age','sex'].includes(k) && typeof v === 'number')
    .map(([k,v]) => ({ name: metricName(k), value: v, unit: catalog.value.find(x => x.key === k)?.unit || '', reference: '按本地规则库判读' }))
  return [...rows, ...(data._custom_metrics || []).map(x => ({ name: x.name, value: x.value, unit: x.unit, reference: x.reference || '未判读' }))]
})

async function loadAudit() {
  if (!isAdmin.value) return
  const result = await staffApi.adminAuditLogs()
  auditLogs.value = result.items || []
}
async function loadPatients() {
  if (!authorized.value) return
  const result = await staffApi.patients(keyword.value)
  patients.value = result.patients || []
}
async function changePatientRole(person, newRole) {
  if (!isAdmin.value || newRole === person.role) return
  try {
    await ElMessageBox.confirm(`确认把 ${person.username} 设为${roleText(newRole)}吗？`, '变更账号权限', { type: 'warning' })
    await staffApi.adminChangeRole(person.username, newRole)
    await loadPatients()
    ElMessage.success('账号角色已修改')
  } catch (error) {
    // 取消操作不修改数据库；其他错误由 HTTP 拦截器提示。
  }
}
async function choosePatient(username) {
  selectedUser.value = username
  selectedRecord.value = null
  diagnoses.value = []
  const result = await staffApi.records(username)
  records.value = (result.records || []).slice().reverse()
}
async function selectRecord(record) {
  selectedRecord.value = await staffApi.record(record.id)
  await loadDiagnoses()
}
async function loadDiagnoses() {
  if (!selectedRecord.value) return
  const data = await staffApi.diagnoses(selectedRecord.value.id)
  diagnoses.value = data.diagnoses || []
}
async function saveDiagnosis() {
  if (!selectedRecord.value || !diagnosis.title || !diagnosis.impression || !diagnosis.advice) {
    ElMessage.warning('请填写标题、临床评估和处理建议')
    return
  }
  saving.value = true
  try {
    await staffApi.diagnose(selectedRecord.value.id, { ...diagnosis })
    Object.assign(diagnosis, { title: '', impression: '', advice: '', follow_up: '' })
    await loadDiagnoses()
    ElMessage.success('诊断意见已保存（原始体检数据未改变）')
  } finally { saving.value = false }
}
function openEditor() {
  if (!isAdmin.value || !selectedRecord.value) return
  const parsed = selectedRecord.value.parsed_data || {}
  editRows.value = Object.entries(parsed)
    .filter(([k, v]) => typeof v === 'number' && !['age'].includes(k) && !k.startsWith('_'))
    .map(([key, value]) => ({ key, value: String(value) }))
  editCustom.value = (parsed._custom_metrics || []).map(x => ({ ...x }))
  editSex.value = parsed.sex || ''
  editAge.value = parsed.age ?? null
  editRaw.value = selectedRecord.value.raw_text || ''
  editorVisible.value = true
}
async function saveAdminEdit() {
  if (!isAdmin.value || !selectedRecord.value) return
  const metrics = {}
  if (editSex.value) metrics.sex = editSex.value
  if (editAge.value != null) metrics.age = editAge.value
  for (const row of editRows.value) {
    if (!row.key || String(row.value).trim() === '') continue
    const n = Number(row.value)
    if (!Number.isFinite(n)) { ElMessage.warning(`${row.key} 不是有效数值`); return }
    if (Object.hasOwn(metrics, row.key)) { ElMessage.warning(`指标 ${row.key} 重复`); return }
    metrics[row.key] = n
  }
  saving.value = true
  try {
    const origin = selectedRecord.value.parsed_data || {}
    const editedRecordId = selectedRecord.value.id
    await staffApi.adminUpdateRecord(editedRecordId, {
      metrics,
      raw_text: editRaw.value,
      check_type: origin._check_type || 'general',
      lab_system: origin._lab_system || null,
      custom_metrics: editCustom.value.filter(x => x.name && x.value !== '')
    })
    editorVisible.value = false
    await choosePatient(selectedUser.value)
    await selectRecord({ id: editedRecordId })
    ElMessage.success('修改成功；旧 AI 解读已清除，请按需重新生成')
  } finally { saving.value = false }
}
async function regenerateReport() {
  if (!isAdmin.value || !selectedRecord.value) return
  saving.value = true
  try {
    await staffApi.adminRegenerateReport(selectedRecord.value.id)
    await selectRecord({ id: selectedRecord.value.id })
    ElMessage.success('已重新生成 AI 解读')
  } finally { saving.value = false }
}
async function removeRecord() {
  if (!isAdmin.value || !selectedRecord.value) return
  await ElMessageBox.confirm('此操作将删除该体检记录及关联医生意见，确认继续？', '管理员删除', { type:'warning' })
  await staffApi.adminDeleteRecord(selectedRecord.value.id)
  await choosePatient(selectedUser.value)
  ElMessage.success('已删除')
}

onMounted(async () => {
  try {
    const profile = await auth.profile()
    role.value = profile?.role ?? profile?.profile?.role ?? 'user'
    accountUsername.value = profile?.username ?? profile?.profile?.username ?? ''
    if (!authorized.value) return
    const [metrics, types] = await Promise.all([api.metricCatalog(), api.checkTypes()])
    catalog.value = metrics.metrics || []
    checkTypes.value = Object.fromEntries((types.types || []).map(x => [x.key, x.name]))
    await loadPatients()
    if (isAdmin.value && section.value === 'audit') await loadAudit()
  } catch (error) {
    ElMessage.error(error?.message || '工作台加载失败')
  } finally { loadingProfile.value = false }
})
watch(section, async (value) => {
  selectedRecord.value = null
  if (isAdmin.value && value === 'audit') await loadAudit()
})
</script>

<style scoped>
.staff-dashboard { display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-bottom:16px; }
.staff-summary {display:flex;flex-direction:column;gap:6px;}
.staff-summary strong {font-size:25px;color:var(--brand,#0e7490);}
.staff-summary small {color:var(--sub,#64748b);}
@media(max-width:850px){.staff-dashboard{grid-template-columns:1fr;}}
.staff-page { padding: 8px 0 30px; }
.staff-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; }
.staff-head h2 { margin:0; font-size:24px; }
.staff-head p { margin:4px 0 0; color:var(--sub, #64748b); }
.staff-layout { display:grid; grid-template-columns:260px minmax(0,1fr); gap:16px; }
.staff-list { margin:0; align-self:start; }
.staff-main { min-width:0; display:flex; flex-direction:column; gap:16px; }
.staff-main > .card { margin:0; }
.staff-section-title { font-weight:700; color:var(--ink,#0f172a); margin-bottom:14px; }
.patient-row { display:flex; flex-direction:column; align-items:stretch; width:100%; padding:11px;
               background:transparent; border:0; border-bottom:1px solid #eef2f6; cursor:pointer; text-align:left; border-radius:8px; }
.patient-row:hover,.patient-row.picked { background:#e6f4f6; }
.patient-name { font-size:14px; font-weight:600; }
.patient-row small { font-size:11px; color:#64748b; }
.role-change { width:100%; margin-top:8px; }
.patients-scroll { margin-top:12px; }
.flex-between { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.action-group { display:flex; gap:6px; }
.report-original { margin-top:16px; padding:12px; background:#f8fafc; border-radius:10px; }
.report-original pre { white-space:pre-wrap; word-break:break-word; font-size:12px; margin-bottom:0; }
.diagnosis-form { margin-top:15px; }
.diagnosis-item { border-top:1px solid #edf1f6; padding:13px 0; }
.diagnosis-item span { display:block; font-size:12px; color:#64748b; }
.diagnosis-item p { white-space:pre-wrap; margin:6px 0; }
.hint { color:#64748b; font-size:12px; }
.edit-scroll { max-height:65vh; overflow:auto; }
.edit-line { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.edit-line :deep(.el-select),.edit-line :deep(.el-input) { flex:1; min-width:0; }
.extra-section { margin-top:18px; }
@media (max-width:950px) { .staff-layout { grid-template-columns:1fr; } }
</style>
