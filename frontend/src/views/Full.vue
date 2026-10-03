<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { current, dataVersion } from '../store'

const lanes = ref<any[]>([])
const error = ref('')

async function load() {
  error.value = ''
  try { lanes.value = (await api('/refills/full')).lanes } catch (e: any) { error.value = e.message || String(e) }
}

onMounted(load)
watch(dataVersion, load)
</script>
<template>
  <h1>满仓</h1>
  <p class="sub">当前点位：{{ current?.code }} · 缺口为 0 的货道（无需补货）</p>
  <div v-if="error" class="vf-error">{{ error }}</div>
  <div class="card">
    <table>
      <thead><tr><th>货道</th><th>商品</th><th>库存</th><th>在途</th><th>容量</th></tr></thead>
      <tbody>
        <tr v-for="l in lanes" :key="l.lane_id">
          <td>{{ l.slot_no }}</td><td>{{ l.sku_name }}</td><td>{{ l.stock }}</td><td>{{ l.in_transit }}</td><td>{{ l.capacity }}</td>
        </tr>
        <tr v-if="!lanes.length"><td colspan="5" class="muted">当前点位暂无满仓货道</td></tr>
      </tbody>
    </table>
  </div>
</template>
