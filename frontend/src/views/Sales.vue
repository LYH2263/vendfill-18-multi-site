<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { current, dataVersion } from '../store'

const rows = ref<any[]>([])
const error = ref('')

async function load() {
  error.value = ''
  try { rows.value = await api('/sales') } catch (e: any) { error.value = e.message || String(e) }
}

onMounted(load)
watch(dataVersion, load)
</script>
<template>
  <h1>销量</h1>
  <p class="sub">当前点位：{{ current?.code }} · 近期出货记录（仅当前点位）</p>
  <div v-if="error" class="vf-error">{{ error }}</div>
  <div class="card">
    <table>
      <thead><tr><th>货道</th><th>商品</th><th>数量</th><th>时间</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)"><td>{{ r.slot_no }}</td><td>{{ r.sku_name }}</td><td>{{ r.qty }}</td><td>{{ r.sold_at }}</td></tr>
        <tr v-if="!rows.length"><td colspan="4" class="muted">当前点位暂无销量记录</td></tr>
      </tbody>
    </table>
  </div>
</template>
