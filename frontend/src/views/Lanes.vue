<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { current, dataVersion } from '../store'

const rows = ref<any[]>([])
const receipt = ref<any>(null)
const error = ref('')
const form = ref({ slot_no: '', sku_name: '', capacity: 10, stock: 0, in_transit: 0 })

async function load() {
  error.value = ''
  try {
    rows.value = await api('/lanes')
    try { receipt.value = await api('/refills/latest') } catch { receipt.value = null }
  } catch (e: any) { error.value = e.message || String(e) }
}

async function add() {
  error.value = ''
  if (!form.value.slot_no.trim() || !form.value.sku_name.trim()) {
    error.value = '货道号与商品名必填'
    return
  }
  try {
    await api('/lanes', { method: 'POST', body: JSON.stringify(form.value) })
    form.value = { slot_no: '', sku_name: '', capacity: 10, stock: 0, in_transit: 0 }
    await load()
  } catch (e: any) { error.value = e.message || String(e) }
}

async function remove(id: number) {
  error.value = ''
  try {
    await api(`/lanes/${id}`, { method: 'DELETE' })
    await load()
  } catch (e: any) { error.value = e.message || String(e) }
}

onMounted(load)
watch(dataVersion, load)
</script>
<template>
  <h1>货道格子</h1>
  <p class="sub">当前点位：{{ current?.code }} · 机面货道网格 · 仅显示当前点位货道</p>
  <div v-if="error" class="vf-error">{{ error }}</div>
  <div class="card">
    <div class="vf-form">
      <input v-model="form.slot_no" placeholder="货道号" style="width:90px" />
      <input v-model="form.sku_name" placeholder="商品名" style="width:130px" />
      <input v-model.number="form.capacity" type="number" min="1" placeholder="容量" style="width:80px" />
      <input v-model.number="form.stock" type="number" min="0" placeholder="库存" style="width:80px" />
      <input v-model.number="form.in_transit" type="number" min="0" placeholder="在途" style="width:80px" />
      <button class="btn" @click="add">添加货道</button>
    </div>
  </div>
  <div class="vf-machine-layout">
    <div class="vf-slot-grid">
      <div v-for="r in rows" :key="r.id" class="vf-slot">
        <button class="vf-slot-del" title="删除货道" @click="remove(r.id)">×</button>
        <div class="vf-slot-no">{{ r.slot_no }}</div>
        <div class="vf-slot-sku">{{ r.sku_name }}</div>
        <div class="vf-slot-bar">
          <div
            class="vf-slot-fill"
            :class="{ 'vf-need': r.gap > 0 }"
            :style="{ width: Math.min(r.fill_pct, 100) + '%' }"
          />
        </div>
        <div class="vf-slot-meta">{{ r.stock }}/{{ r.capacity }} · 缺 {{ r.gap }}</div>
      </div>
      <div v-if="!rows.length" class="muted" style="padding:0.5rem">当前点位暂无货道，请在上方添加</div>
    </div>
    <aside class="vf-receipt" v-if="receipt">
      <h2>*** 最新补货单 #{{ receipt.id }} ***</h2>
      <div class="vf-receipt-line" v-for="l in receipt.lines" :key="l.lane_id">
        <span>{{ l.slot_no }} {{ l.sku_name }}</span>
        <span>x{{ l.fill_qty }}</span>
      </div>
      <p class="muted" style="margin:0.75rem 0 0;font-size:0.72rem;color:#6a5e48;text-align:center">
        — 机面打印预览 —
      </p>
    </aside>
    <aside class="vf-receipt" v-else>
      <h2>*** 补货单 ***</h2>
      <p style="text-align:center;font-size:0.78rem">当前点位暂无补货单<br />请到「补货小票」生成</p>
    </aside>
  </div>
</template>
