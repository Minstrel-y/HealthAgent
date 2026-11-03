<template>
  <div>
    <div class="page-title">个人设置</div>
    <p class="muted">头像、字号、性别等偏好会同步到你的账号；性别会影响部分指标的参考区间。</p>

    <div v-if="loading" class="card"><el-skeleton :rows="6" animated /></div>

    <div v-else class="set-grid">
      <!-- 左：头像与基本信息 -->
      <div class="card">
        <div class="card-title">头像与基本信息</div>

        <div class="avatar-block">
          <div class="avatar-preview">
            <img v-if="form.avatar" :src="form.avatar" alt="头像" />
            <span v-else>{{ initial }}</span>
          </div>
          <div style="flex:1;min-width:0;">
            <el-button size="small" :loading="uploading" @click="pickFile">上传图片</el-button>
            <input ref="fileRef" type="file" accept="image/*" hidden @change="onFile" />
            <p class="faint" style="margin:6px 0 10px;">支持 png / jpg / webp，不超过 3MB</p>
            <div class="preset-row">
              <span v-for="(p, i) in presets" :key="i" class="preset" :class="{ active: form.avatar === p }"
                    @click="usePreset(p)">{{ p }}</span>
              <span class="preset none" :class="{ active: !form.avatar }" @click="usePreset('')">无头像</span>
            </div>
          </div>
        </div>

        <div class="form-row">
          <label>昵称</label>
          <el-input v-model="form.nickname" placeholder="显示用的名字" style="max-width:240px;" />
        </div>

        <div class="form-row">
          <label>性别</label>
          <el-radio-group v-model="form.sex">
            <el-radio value="male">男</el-radio>
            <el-radio value="female">女</el-radio>
            <el-radio value="unknown">不填</el-radio>
          </el-radio-group>
          <span class="faint">肌酐、尿酸的参考区间男女不同，填写后判读更准确</span>
        </div>

        <div class="form-row">
          <label>出生日期</label>
          <el-input v-model="form.birthday" placeholder="YYYY-MM-DD" style="max-width:240px;" />
        </div>
      </div>

      <!-- 右：显示偏好 -->
      <div class="card">
        <div class="card-title">显示偏好</div>

        <div class="font-block">
          <div class="font-head">
            <span>界面字号</span>
            <b>{{ Math.round(fontScale * 100) }}%</b>
          </div>
          <el-slider v-model="fontScale" :min="85" :max="140" :step="5" show-stops
                     @input="applyScale" @change="save" />
          <div class="font-preview">
            <div class="pv-title">预览效果</div>
            <div class="pv-text">
              收缩压 138 mmHg 属于临界范围，建议控制盐分摄入并保持规律有氧运动。
            </div>
            <el-button size="small" style="margin-top:10px;">示例按钮</el-button>
          </div>
          <el-button text size="small" @click="resetScale">恢复默认 100%</el-button>
        </div>

        <el-divider />

        <div class="save-bar">
          <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
          <el-button @click="load">放弃修改</el-button>
        </div>

        <p class="faint" style="margin-top:12px;">
          字号会作用于整个界面（含卡片、图表文字），并随账号同步；<br />
          下次在其他设备登录会自动应用。
        </p>
      </div>
    </div>

    <div class="card" style="margin-top:16px;">
      <div class="card-title">账号</div>
      <div class="form-row">
        <label>用户名</label>
        <span style="color:var(--ink);font-weight:600;">{{ form.username }}</span>
        <el-tag size="small" type="info" style="margin-left:8px;">注册于 {{ form.created_at }}</el-tag>
      </div>
      <el-button size="small" @click="logout">退出登录</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(true)
const saving = ref(false)
const uploading = ref(false)
const fileRef = ref(null)
const form = ref({ username: '', nickname: '', avatar: '', sex: 'unknown', birthday: '', font_scale: 1, created_at: '' })
const fontScale = ref(100)
const presets = ['🧑‍⚕️', '🩺', '💪', '🧘', '🏃', '🫀', '😀', '🐱']

// 字号即时生效：写入根环境变量，预览与全站同步变化
const applyScale = (v) => {
  document.documentElement.style.setProperty('--font-scale', String((v || 100) / 100))
}

const initial = computed(() => (form.value.nickname || form.value.username || 'U').slice(0, 1).toUpperCase())

const load = async () => {
  loading.value = true
  try {
    const p = await auth.profile()
    form.value = p
    fontScale.value = Math.round((p.font_scale || 1) * 100)
    applyScale(fontScale.value)
  } finally {
    loading.value = false
  }
}

const save = async () => {
  saving.value = true
  try {
    await auth.updateProfile({
      nickname: form.value.nickname,
      avatar: form.value.avatar,
      sex: form.value.sex,
      birthday: form.value.birthday,
      font_scale: fontScale.value / 100
    })
    localStorage.setItem('ha_font_scale', String(fontScale.value / 100))
    ElMessage.success('设置已保存')
  } finally {
    saving.value = false
  }
}

const pickFile = () => fileRef.value?.click()

const onFile = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  if (file.size > 3 * 1024 * 1024) {
    ElMessage.warning('图片不能超过 3MB')
    return
  }
  uploading.value = true
  try {
    const res = await auth.uploadAvatar(file)
    form.value.avatar = res.avatar
    await save()
  } catch {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
    e.target.value = ''
  }
}

const usePreset = (v) => {
  form.value.avatar = v
  save()
}

const resetScale = () => {
  fontScale.value = 100
  applyScale(100)
  save()
}

const logout = () => {
  localStorage.removeItem('ha_token')
  localStorage.removeItem('ha_user')
  router.replace('/login')
}

onMounted(load)
onBeforeUnmount(() => {
  // 离开页面时恢复账号里的字号，避免预览未保存的值残留
  applyScale(Math.round((form.value.font_scale || 1) * 100))
})
</script>

<style scoped>
.set-grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 16px; align-items: start; margin-top: 16px; }

.avatar-block { display: flex; gap: 18px; align-items: flex-start; margin-bottom: 18px; }
.avatar-preview {
  width: 76px; height: 76px; flex: none; border-radius: 22px;
  display: grid; place-items: center; overflow: hidden;
  background: linear-gradient(140deg, var(--brand), var(--accent)); color: #fff;
  font-size: 26px; font-weight: 700; box-shadow: var(--sh-sm);
}
.avatar-preview img { width: 100%; height: 100%; object-fit: cover; }

.preset-row { display: flex; flex-wrap: wrap; gap: 6px; }
.preset {
  width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center;
  background: #f1f5f9; cursor: pointer; font-size: 15px; border: 1px solid transparent; transition: all .15s ease;
}
.preset:hover { background: var(--brand-soft); }
.preset.active { border-color: var(--brand); background: var(--brand-soft); }
.preset.none { width: auto; padding: 0 8px; font-size: 12px; color: var(--sub); }

.form-row { display: flex; align-items: center; gap: 12px; padding: 9px 0; flex-wrap: wrap; }
.form-row label { width: 68px; flex: none; font-size: 13px; color: var(--sub); }

.font-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 2px; }
.font-head span { font-size: 13px; color: var(--sub); }
.font-head b { font-size: 18px; color: var(--brand); }

.font-preview {
  margin-top: 14px; padding: 14px; border: 1px dashed var(--line); border-radius: var(--r-md); background: #fbfdfe;
}
.pv-title { font-size: 15px; font-weight: 600; color: var(--ink); margin-bottom: 6px; }
.pv-text { font-size: 14px; color: var(--text); line-height: 1.7; }

.save-bar { display: flex; gap: 10px; }

@media (max-width: 1000px) { .set-grid { grid-template-columns: 1fr; } }
</style>
