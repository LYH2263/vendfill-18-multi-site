<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { current, dataVersion } from '../store'

const data = ref<any>(null)
const history = ref<any[]>([])
const error = ref('')

async function load() {
  error.value = ''
  try {
    history.value = await api('/refills')
    try { data.value = await api('/refills/latest') } catch { data.value = null }
  } catch (e: any) { error.value = e.message || String(e) }
}

async function run() {
  error.value = ''
  try {
    data.value = await api('/refills/run', { method: 'POST' })
    await load()
  } catch (e: any) { error.value = e.message || String(e) }
}

async function voidOrder(id: number) {
  error.value = ''
  try {
    await api(`/refills/${id}/void`, { method: 'POST' })
    await load()
  } catch (e: any) { error.value = e.message || String(e) }
}

onMounted(load)
watch(dataVersion, load)
</script>
<template>
  <h1>补货小票</h1>
  <p class="sub">当前点位：{{ current?.code }} · gap = 容量 − 库存 − 在途 · 生成只作用于当前点位</p>
  <div v-if="error" class="vf-error">{{ error }}</div>
  <button class="btn" @click="run">生成补货单</button>
  <div style="margin-top:1rem" v-if="data">
    <div class="vf-receipt">
      <h2>*** VendFill 补货单 #{{ data.id }} ***</h2>
      <div class="vf-receipt-line" style="font-weight:700;border-bottom:2px dashed #8a7e64">
        <span>货道 / 商品</span><span>补量</span>
      </div>
      <div class="vf-receipt-line" v-for="l in data.lines" :key="l.lane_id">
        <span>{{ l.slot_no }} {{ l.sku_name }}
          <small>({{ l.status === 'need_fill' ? '待补' : l.status === 'full' ? '满仓' : '超占' }})</small>
        </span>
        <span>{{ l.fill_qty }} / 缺{{ l.gap }}</span>
      </div>
      <p style="text-align:center;margin:1rem 0 0;font-size:0.72rem;color:#6a5e48">谢谢使用 · 请核对后装机</p>
    </div>
  </div>
  <p v-else class="muted" style="margin-top:1rem">当前点位暂无补货单，点击上方按钮生成。</p>
  <div class="card" style="margin-top:1rem">
    <table>
      <thead><tr><th>单号</th><th>时间</th><th>状态</th><th>建议补货总量</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="o in history" :key="o.id">
          <td>#{{ o.id }}</td>
          <td>{{ o.created_at }}</td>
          <td>
            <span class="badge" :class="o.status === 'void' ? 'badge-bad' : 'badge-ok'">
              {{ o.status === 'void' ? '已作废' : '有效' }}
            </span>
          </td>
          <td>{{ o.total_fill }}</td>
          <td>
            <button v-if="o.status !== 'void'" class="btn btn-ghost btn-sm" @click="voidOrder(o.id)">作废</button>
          </td>
        </tr>
        <tr v-if="!history.length"><td colspan="5" class="muted">当前点位暂无补货单</td></tr>
      </tbody>
    </table>
  </div>
</template>
