<!--
  诱因与关联疾病分析：数据来自后端本地规则库（backend/rules.py），
  不调用大模型，因此每条结论都可追溯到静态知识条目。
-->
<template>
  <div class="insight-wrap">
    <div class="insight-head">
      <div>
        <div class="card-title" style="margin-bottom:4px;">异常诱因 · 关联疾病分析</div>
        <span class="muted">基于本地规则库推理，不调用模型；标 ★ 的诱因与你本次的数据吻合</span>
      </div>
      <el-button size="small" text @click="visible = !visible">
        {{ visible ? '收起' : '展开' }}（{{ items.length }} 项）
      </el-button>
    </div>

    <div v-show="visible">
      <!-- 交叉组合结论 -->
      <div v-if="cross.length" class="cross-block">
        <div class="block-label">多项指标组合提示</div>
        <div v-for="c in cross" :key="c.title" class="cross-card" :class="levelClass(c.level)">
          <div class="cross-top">
            <span class="chip">{{ c.level }}</span>
            <b>{{ c.title }}</b>
            <span class="faint">{{ c.names.join(' + ') }}</span>
          </div>
          <p>{{ c.detail }}</p>
        </div>
      </div>

      <!-- 单指标诱因 -->
      <div v-if="items.length" class="insight-grid">
        <div v-for="it in items" :key="it.key" class="insight-card">
          <div class="ic-head">
            <div class="ic-title">
              <b>{{ it.name }}</b>
              <em class="tag" :class="it.status">{{ it.status_label }}</em>
            </div>
            <span class="ic-value" :style="{ color: valueColor(it.status) }">
              {{ it.value }}<span class="u">{{ it.unit }}</span>
            </span>
          </div>

          <p class="ic-summary">{{ it.summary }}</p>

          <div class="ic-label">可能诱因</div>
          <ul class="ic-causes">
            <li v-for="(c, i) in it.top_causes" :key="i" :class="{ hit: c.hit }">
              <span class="bulb">{{ c.hit ? '★' : '·' }}</span>
              <span class="txt">{{ c.text }}</span>
              <em class="ctag">{{ c.tag }}</em>
            </li>
          </ul>

          <div class="ic-label">关联疾病 / 风险</div>
          <div class="ic-tags">
            <span v-for="d in it.diseases" :key="d.name" class="dis" :class="disClass(d.level)">
              {{ d.name }}<i>{{ d.level }}</i>
            </span>
          </div>

          <el-button size="small" text type="primary" style="padding:0;margin-top:10px;" @click="openRule(it)">
            查看完整诱因与应对建议 →
          </el-button>
        </div>
      </div>

      <div v-else class="empty-tip">本次所有指标都在正常范围，没有需要分析的异常项 🎉</div>

      <p class="faint" style="margin-top:12px;">{{ disclaimer }}</p>
    </div>

    <!-- 单指标完整规则抽屉 -->
    <el-drawer v-model="drawer" :title="rule ? rule.title : ''" size="520px">
      <div v-if="rule" class="rule-body">
        <p class="muted">{{ rule.summary }}</p>

        <div class="sec-title">可能诱因<span class="faint">按与你的数据吻合度排序</span></div>
        <div v-for="(c, i) in rule.causes" :key="i" class="rule-row" :class="{ hit: c.hit }">
          <span class="bulb">{{ c.hit ? '★' : '·' }}</span>
          <span class="txt">{{ c.text }}</span>
          <em class="ctag">{{ c.tag }}</em>
          <span v-if="c.hint" class="hint">{{ c.hint }}</span>
        </div>

        <div class="sec-title">关联疾病</div>
        <table class="rule-table">
          <tr v-for="d in rule.diseases" :key="d.name">
            <td>{{ d.name }}</td>
            <td><em class="dis" :class="disClass(d.level)">{{ d.level }}</em></td>
          </tr>
        </table>

        <div class="sec-title">建议进一步检查</div>
        <ul class="rule-list">
          <li v-for="(c, i) in rule.checks" :key="i">{{ c }}</li>
        </ul>

        <div class="sec-title">生活干预要点</div>
        <ul class="rule-list action">
          <li v-for="(a, i) in rule.actions" :key="i">{{ a }}</li>
        </ul>

        <p class="faint" style="margin-top:16px;">{{ disclaimer }}</p>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { api } from '@/api'

const props = defineProps({
  recordId: { type: [Number, String], default: null }
})

const items = ref([])
const cross = ref([])
const disclaimer = ref('')
const visible = ref(true)
const drawer = ref(false)
const rule = ref(null)

const load = async () => {
  try {
    const res = await api.insights(props.recordId)
    items.value = res.items || []
    cross.value = res.cross || []
    disclaimer.value = res.disclaimer || ''
  } catch {
    items.value = []
    cross.value = []
  }
}

const openRule = async (it) => {
  drawer.value = true
  rule.value = null
  try {
    rule.value = await api.metricRule(it.key)
  } catch {
    rule.value = null
  }
}

const valueColor = (s) => ({ danger: 'var(--danger)', warning: 'var(--warn)', low: 'var(--info)' }[s] || 'var(--ink)')
const levelClass = (lv) => (lv.includes('尽快') ? 'urgent' : 'warn')
const disClass = (lv) => {
  if (['直接相关', '最常见', '急症风险'].includes(lv)) return 'high'
  if (['尽快复查'].includes(lv)) return 'high'
  if (['常见共病', '需排查'].includes(lv)) return 'mid'
  return 'low'
}

watch(() => props.recordId, load)
onMounted(load)
</script>

<style scoped>
.insight-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }

/* 交叉组合 */
.block-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--sub);
  letter-spacing: .5px;
  margin: var(--sp-4) 0 var(--sp-2);
}
.cross-block { display: grid; gap: 10px; }
.cross-card {
  border: 1px solid var(--line);
  border-left: 3px solid var(--warn);
  background: #fff;
  border-radius: var(--r-md);
  padding: 12px 16px;
  box-shadow: var(--sh-xs);
}
.cross-card.urgent { border-left-color: var(--danger); }
.cross-card.warn { border-left-color: var(--warn); }
.cross-top { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.cross-top .chip {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--warn-bg);
  color: var(--warn);
}
.cross-card.urgent .chip { background: var(--danger-bg); color: var(--danger); }
.cross-card p { margin: 6px 0 0; color: var(--sub); font-size: 13px; line-height: 1.75; }

/* 指标卡 */
.insight-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sp-3);
  margin-top: var(--sp-3);
}
.insight-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  padding: var(--sp-4);
  box-shadow: var(--sh-xs);
  transition: box-shadow .2s ease, transform .2s ease;
}
.insight-card:hover { transform: translateY(-2px); box-shadow: var(--sh-sm); }
.ic-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.ic-title { display: flex; align-items: center; gap: 8px; }
.ic-title b { font-size: 14.5px; color: var(--ink); }
.ic-value { font-size: 20px; font-weight: 700; letter-spacing: -.3px; }
.ic-value .u { font-size: 12px; font-weight: 500; color: var(--sub); margin-left: 2px; }

.ic-summary { margin: 8px 0 0; font-size: 12.5px; color: var(--sub); line-height: 1.7; }

.ic-label {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--faint);
  letter-spacing: .5px;
  margin: 12px 0 6px;
}
.ic-causes { list-style: none; margin: 0; padding: 0; display: grid; gap: 5px; }
.ic-causes li, .rule-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text);
  padding: 4px 8px;
  border-radius: 8px;
}
.ic-causes li.hit, .rule-row.hit { background: var(--brand-soft); color: var(--brand-deep); font-weight: 500; }
.bulb { flex: none; color: var(--brand); font-weight: 700; }
.txt { flex: 1; min-width: 0; }
.ctag {
  flex: none;
  font-style: normal;
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 6px;
  background: #f1f5f9;
  color: var(--sub);
}
.ic-causes li.hit .ctag, .rule-row.hit .ctag { background: #fff; color: var(--brand); }

.ic-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.dis {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 8px;
  background: #f1f5f9;
  color: var(--text);
}
.dis i { font-style: normal; font-size: 10.5px; color: var(--faint); }
.dis.high { background: var(--danger-bg); color: var(--danger); }
.dis.high i { color: var(--danger); opacity: .7; }
.dis.mid { background: var(--warn-bg); color: var(--warn); }
.dis.mid i { color: var(--warn); opacity: .7; }

.empty-tip { text-align: center; padding: 32px; color: var(--sub); }

/* 抽屉 */
.sec-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
  margin: 18px 0 8px;
}
.hint { flex: none; font-size: 11px; color: var(--brand); }
.rule-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.rule-table td { padding: 6px 0; border-bottom: 1px solid var(--line-soft); }
.rule-table td:last-child { text-align: right; }
.rule-list { margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.9; color: var(--text); }
.rule-list.action li { color: var(--brand-deep); }

@media (max-width: 900px) {
  .insight-grid { grid-template-columns: minmax(0, 1fr); }
}
</style>
